import base64
import json
import random
import string
import time
import requests

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.asymmetric import padding

@service
def login_api():
    """
    Logs into Sungrow API and stores token in input_text.token
    """

    username = pyscript.app_config["suncloud_username"]
    password = pyscript.app_config["suncloud_password"]
    appkey = pyscript.app_config["suncloud_appkey"]
    x_access_key = pyscript.app_config["suncloud_secret"]
    public_key_base64 = pyscript.app_config["suncloud_rsa_key"]
    login_url = "https://gateway.isolarcloud.eu/openapi/login"

    # Generate AES secret key and encrypt it with RSA public key
    unenc_key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    x_random_secret_key = rsa_encrypt_secret_key(unenc_key, public_key_base64)

    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))

    payload = {
        "api_key_param": {
            "nonce": nonce,
            "timestamp": timestamp
        },
        "appkey": appkey,
        "login_type": "1",
        "user_account": username,
        "user_password": password
    }

    headers = {
        "User-Agent": "Home Assistant",
        "x-access-key": x_access_key,
        "x-random-secret-key": x_random_secret_key,
        "Content-Type": "application/json",
        "sys_code": "901"
    }

    encrypted_body = aes_encrypt(json.dumps(payload), unenc_key)

    try:
        response = task.executor(requests.post, login_url, headers=headers, data=encrypted_body)

        if response.status_code == 200:
            decrypted = aes_decrypt(response.text, unenc_key)
            token = decrypted.get("result_data", {}).get("token", "")
            state.set("input_text.token", token)
            log.info(f"[LOGIN] Success. Token set: {token[:6]}...")

        else:
            log.error(f"[LOGIN] HTTP {response.status_code}: {response.text}")
            state.set("input_text.token", "Error")

    except Exception as e:
        log.error(f"[LOGIN] Exception: {e}")
        state.set("input_text.token", "Error")


def rsa_encrypt_secret_key(secret: str, public_key_base64: str) -> str:
    try:
        pubkey_bytes = base64.urlsafe_b64decode(public_key_base64.strip())
        public_key = serialization.load_der_public_key(pubkey_bytes, backend=default_backend())
        encrypted = public_key.encrypt(secret.encode("utf-8"), padding.PKCS1v15())
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
    except Exception as e:
        log.error(f"[RSA] Encryption error: {e}")
        return "INVALID_RSA"


def aes_encrypt(content: str, password: str) -> str:
    try:
        key = password.encode("utf-8").ljust(16)[:16]
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = PKCS7(128).padder()
        padded = padder.update(content.encode("utf-8")) + padder.finalize()
        return encryptor.update(padded) + encryptor.finalize()
    except Exception as e:
        log.error(f"[AES] Encrypt error: {e}")
        return ""


def aes_decrypt(encrypted_hex: str, password: str):
    try:
        cipher_bytes = bytes.fromhex(encrypted_hex)
        key = password.encode("utf-8").ljust(16)[:16]
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(cipher_bytes) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        original = unpadder.update(padded) + unpadder.finalize()
        return json.loads(original.decode("utf-8"))
    except Exception as e:
        log.error(f"[AES] Decrypt error: {e}")
        return {}
        

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
