import aiohttp
import base64
import json
import logging
import random
import string
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

_LOGGER = logging.getLogger(__name__)


def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def get_secret_key(key):
    return key.encode("utf-8").ljust(16)[:16]


def encrypt(content, password):
    key = get_secret_key(password)
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = PKCS7(128).padder()
    padded = padder.update(content.encode("utf-8")) + padder.finalize()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return encrypted.hex().upper()


def decrypt(content, password):
    data = bytes.fromhex(content)
    key = get_secret_key(password)
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(data) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    unpadded = unpadder.update(decrypted) + unpadder.finalize()
    return unpadded.decode("utf-8")


def public_encrypt(data, public_key_base64):
    try:
        public_key_bytes = base64.urlsafe_b64decode(public_key_base64.strip())
        public_key = serialization.load_der_public_key(public_key_bytes, backend=default_backend())
    except Exception as e:
        _LOGGER.error(f"Failed to load public key: {e}")
        return None

    encrypted = public_key.encrypt(
        data.encode("utf-8"),
        rsa_padding.PKCS1v15()
    )
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


async def post_request(hass, config, endpoint, payload, token=None):
    unenc_secret = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    x_random_secret_key = public_encrypt(unenc_secret, config["RSA_public"])
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))

    headers = {
        "User-Agent": "Home Assistant",
        "x-access-key": config["sung_secret"],
        "x-random-secret-key": x_random_secret_key,
        "Content-Type": "application/json",
        "sys_code": "901"
    }

    if token:
        headers["token"] = token

    payload["api_key_param"] = {
        "nonce": nonce,
        "timestamp": timestamp
    }

    encrypted_payload = encrypt(json.dumps(payload), unenc_secret)
    url = f"{config['base_url']}{endpoint}"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=encrypted_payload) as resp:
            if resp.status != 200:
                _LOGGER.error(f"Request failed: {resp.status}")
                return None
            try:
                response_encrypted = await resp.text()
                decrypted = decrypt(response_encrypted, unenc_secret)
                return json.loads(decrypted)
            except Exception as e:
                _LOGGER.error(f"Decryption or JSON parsing failed: {e}")
                return None

