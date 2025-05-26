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


# 🔐 1. Login Service
@service
def suncloud_login_api():
    username = app_config["suncloud_username"]
    password = app_config["suncloud_password"]
    appkey = app_config["suncloud_appkey"]
    x_access_key = app_config["suncloud_secret"]
    public_key_base64 = app_config["suncloud_rsa_key"]
    login_url = "https://gateway.isolarcloud.eu/openapi/login"

    unenc_key = generate_random_key()
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
            log.info(f"[LOGIN] Token received: {token[:6]}...")
        else:
            log.error(f"[LOGIN] HTTP {response.status_code}: {response.text}")
            state.set("input_text.token", "Error")
    except Exception as e:
        log.error(f"[LOGIN] Exception: {e}")
        state.set("input_text.token", "Error")


# ☀️ 2. Get Plant List
@service
def suncloud_get_plant_list(curPage: int = 1, size: int = 10):
    token = state.get("input_text.token")
    if not token or token == "Error":
        log.error("[PLANT LIST] No valid token. Run suncloud_login_api first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getPowerStationList"
    headers = {"Content-Type": "application/json", "token": token}
    payload = {"curPage": curPage, "size": size}

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            result = response.json()
            plants = result.get("result_data", {}).get("pageList", [])
            if plants:
                ps_id = plants[0].get("ps_id")
                ps_name = plants[0].get("ps_name")
                state.set("sensor.plant_id", ps_id)
                log.info(f"[PLANT LIST] '{ps_name}' ID: {ps_id}")
            else:
                log.warning("[PLANT LIST] No plants found")
        else:
            log.error(f"[PLANT LIST] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.error(f"[PLANT LIST] Exception: {e}")


# ⚙️ 3. Get Device List
@service
def suncloud_get_device_list():
    token = state.get("input_text.token")
    ps_id = state.get("sensor.plant_id")
    if not token or token == "Error":
        log.error("[DEVICE LIST] No valid token. Run suncloud_login_api first.")
        return
    if not ps_id:
        log.error("[DEVICE LIST] No plant ID. Run suncloud_get_plant_list first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getDeviceList"
    headers = {"Content-Type": "application/json", "token": token}
    payload = {"curPage": 1, "size": 50, "ps_id": ps_id}

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            result = response.json()
            devices = result.get("result_data", {}).get("pageList", [])
            for dev in devices:
                if dev.get("device_type") == 7:
                    dev_sn = dev.get("device_sn")
                    log.info(f"[DEVICE LIST] Found meter SN: {dev_sn}")
                    state.set("sensor.meter_sn", dev_sn)
                    return
            log.warning("[DEVICE LIST] No meter (type 7) found.")
        else:
            log.error(f"[DEVICE LIST] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.error(f"[DEVICE LIST] Exception: {e}")


# 🧠 4. Get ps_key from meter SN
@service
def suncloud_get_plant_info():
    token = state.get("input_text.token")
    meter_sn = state.get("sensor.meter_sn")
    if not token or token == "Error":
        log.error("[PLANT INFO] Invalid token.")
        return
    if not meter_sn:
        log.error("[PLANT INFO] No meter SN. Run suncloud_get_device_list first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getPowerStationDetail"
    headers = {"Content-Type": "application/json", "token": token}
    payload = {"sn": meter_sn, "is_get_ps_remarks": "1"}

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            result = response.json()
            data = result.get("result_data", {})
            ps_key = data.get("ps_key", "")
            ps_name = data.get("ps_name", "unknown")
            if ps_key:
                state.set("input_text.ps_key", ps_key)
                log.info(f"[PLANT INFO] ps_key for {ps_name}: {ps_key}")
            else:
                log.warning("[PLANT INFO] ps_key not returned.")
        else:
            log.error(f"[PLANT INFO] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.error(f"[PLANT INFO] Exception: {e}")


# 📊 5. Discover telemetry points
@service
def suncloud_get_suncloud_points():
    token = state.get("input_text.token")
    if not token or token == "Error":
        log.error("[POINTS] Invalid token. Run suncloud_login_api first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getOpenPointInfo"
    headers = {"Content-Type": "application/json", "token": token}
    payload = {
        "device_type": 11,
        "type": 2,
        "curPage": 1,
        "size": 999,
        "device_model_id": "367701"
    }

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            result = response.json()
            points = result.get("result_data", {}).get("pageList", [])
            ids = [str(p["point_id"]) for p in points if "point_id" in p]
            state.set("input_select.telemetry_points", {"options": ids})
            log.info(f"[POINTS] {len(ids)} telemetry points stored.")
        else:
            log.error(f"[POINTS] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.error(f"[POINTS] Exception: {e}")


# 🔐 Shared Helpers
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

def generate_random_key(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

