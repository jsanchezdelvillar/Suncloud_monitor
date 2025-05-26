import aiohttp
import json
import logging
import base64
import random
import string
import time

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.asymmetric import padding

_LOGGER = logging.getLogger(__name__)


def get_secret_key(key: str):
    return key.encode("utf-8").ljust(16)[:16]


def encrypt(content: str, password: str):
    try:
        password_bytes = get_secret_key(password)
        cipher = Cipher(algorithms.AES(password_bytes), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = PKCS7(128).padder()
        padded_data = padder.update(content.encode("utf-8")) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        return encrypted_data.hex().upper()
    except Exception as e:
        _LOGGER.error(f"Encryption error: {e}")
        return None


def decrypt(content: str, password: str):
    try:
        decrypt_from = bytes.fromhex(content)
        password_bytes = get_secret_key(password)
        cipher = Cipher(algorithms.AES(password_bytes), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded_data = decryptor.update(decrypt_from) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        original = unpadder.update(decrypted_padded_data) + unpadder.finalize()
        return json.loads(original.decode("utf-8"))
    except Exception as e:
        _LOGGER.error(f"Decryption error: {e}")
        return None


def public_encrypt(data: str, public_key_base64: str):
    try:
        public_key_bytes = base64.urlsafe_b64decode(public_key_base64.strip())
        public_key = serialization.load_der_public_key(public_key_bytes, backend=default_backend())
        encrypted = public_key.encrypt(
            data.encode("utf-8"),
            padding.PKCS1v15()
        )
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
    except Exception as e:
        _LOGGER.error(f"RSA public key encryption error: {e}")
        return None


def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_secret_key(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def post_request(endpoint: str, payload: dict, config: dict, token: str = None):
    base_url = config.get("base_url", "https://gateway.isolarcloud.eu")
    public_key_base64 = config.get("suncloud_rsa_key")
    appkey = config.get("suncloud_appkey")
    x_access_key = config.get("suncloud_secret")

    unenc_key = generate_random_secret_key()
    x_random_secret_key = public_encrypt(unenc_key, public_key_base64)
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))

    wrapped_payload = {
        "api_key_param": {
            "nonce": nonce,
            "timestamp": timestamp
        },
        "appkey": appkey,
        **payload
    }

    headers = {
        "User-Agent": "Home Assistant",
        "x-access-key": x_access_key,
        "x-random-secret-key": x_random_secret_key,
        "Content-Type": "application/json",
        "sys_code": "901"
    }

    if token:
        headers["token"] = token

    encrypted_body = encrypt(json.dumps(wrapped_payload), unenc_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}{endpoint}", headers=headers, data=encrypted_body) as resp:
                text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error(f"API {endpoint} failed: {resp.status} {text}")
                    return None
                return decrypt(text, unenc_key)
    except Exception as e:
        _LOGGER.error(f"post_request exception: {e}")
        return None
