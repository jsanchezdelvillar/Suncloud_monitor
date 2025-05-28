import base64
import json
import random
import string
import time
import aiohttp
import builtins
import yaml
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

CONFIG_PATH = "/config/custom_components/suncloud_monitor/config_storage.yaml"

# ============================================
# 🧠 CONFIG LOADER & SAVER FOR PERSISTENT DATA
# ============================================

def load_suncloud_config():
    try:
        with builtins.open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        log.error(f"[CONFIG] ❌ Failed to load config: {e}")
        return {}

def save_suncloud_config(ps_key=None, sn=None, new_points: dict = None):
    config = load_suncloud_config()
    if ps_key:
        config["ps_key"] = ps_key
    if sn:
        config["sn"] = sn
    if new_points:
        config.setdefault("points", {}).update(new_points)
    try:
        with builtins.open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f)
        log.info("[CONFIG] ✅ Config saved")
    except Exception as e:
        log.error(f"[CONFIG] ❌ Write failed: {e}")

# ========================
# 🔐 ENCRYPTION UTILITIES
# ========================

def rsa_encrypt_secret_key(secret: str, public_key_base64: str) -> str:
    log.info(f"[RSA] Encripting {secret} with {public_key_base64}")
    try:
        pubkey_bytes = base64.urlsafe_b64decode(public_key_base64.strip())
        public_key = serialization.load_der_public_key(pubkey_bytes, backend=default_backend())
        encrypted = public_key.encrypt(secret.encode("utf-8"), rsa_padding.PKCS1v15())
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
    except Exception as e:
        log.error(f"[RSA] ❌ Error: {e}")
        return "ENC_ERR"

def aes_encrypt(content: str, password: str) -> str:
    log.info(f"[AES] Encripting {content} with {password}")
    try:
        key = password.encode("utf-8").ljust(16)[:16]
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        padder = PKCS7(128).padder()
        padded = padder.update(content.encode("utf-8")) + padder.finalize()
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded) + encryptor.finalize()
        return encrypted.hex().upper()
    except Exception as e:
        log.error(f"[AES] ❌ Encrypt error: {e}")
        return ""

def aes_decrypt(content: str, password: str):
    log.info(f"[AES] Decrypting {content} with {password}")
    try:
        key = password.encode("utf-8").ljust(16)[:16]
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(bytes.fromhex(content)) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        unpadded = unpadder.update(decrypted) + unpadder.finalize()
        return json.loads(unpadded.decode("utf-8"))
    except Exception as e:
        log.error(f"[AES] ❌ Decrypt error: {e}")
        return {}

# ====================
# 🧠 Misc Utils
# ====================

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_key(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def build_headers(secret_key_encrypted, access_key, token=None):
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "sys_code": "901",
        "x-access-key": access_key,  # ✅ static API key
        "x-random-secret-key": secret_key_encrypted,  # ✅ RSA-encrypted AES key
    }
    if token:
        headers["token"] = token
    log.info(f"[HEA] Headers: {headers}")
    return headers

def build_encrypted_payload(original_payload, appkey, token, unenc_key):
    payload = {
        "appkey": appkey,
        "token": token,
        "lang": "_en_US",
        "api_key_param": {
            "nonce": generate_nonce(),
            "timestamp": str(int(time.time() * 1000))
        }
    }
    payload.update(original_payload)
    log.info(f"[PAY] Payload: {payload}")
    return aes_encrypt(json.dumps(payload), unenc_key)

# ====================
# 🔐 LOGIN SERVICE
# ====================

@service
async def suncloud_login_api():
    username = pyscript.app_config["username"]
    password = pyscript.app_config["password"]
    appkey = pyscript.app_config["appkey"]
    access_key = pyscript.app_config["access_key"]
    public_key = pyscript.app_config["rsa_key"]

    url = "https://gateway.isolarcloud.eu/openapi/login"
    unenc_key = generate_random_key()
    encrypted_key = rsa_encrypt_secret_key(unenc_key, public_key)

    payload = {
        "api_key_param": {
            "nonce": generate_nonce(),
            "timestamp": str(int(time.time() * 1000))
        },
        "appkey": appkey,
        "login_type": "1",
        "user_account": username,
        "user_password": password
    }

    headers = {
        "User-Agent": "Home Assistant",
        "x-access-key": access_key,
        "x-random-secret-key": encrypted_key,
        "Content-Type": "application/json",
        "sys_code": "901"
    }

    encrypted_body = aes_encrypt(json.dumps(payload), unenc_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=encrypted_body) as response:
                raw = await response.text()
                decrypted = aes_decrypt(raw, unenc_key)
                if decrypted.get("result_code") == "1" and decrypted.get("result_data", {}).get("login_state") == "1":
                    token = decrypted["result_data"].get("token")
                    state.set("input_text.token", token)
                    log.info(f"[LOGIN] ✅ Token stored: {token[:6]}...")
                else:
                    log.error("[LOGIN] ❌ Invalid login response")
    except Exception as e:
        log.error(f"[LOGIN] ❌ Exception: {e}")

# ================================
# 🌱 GET PLANT LIST
# ================================

@service
async def suncloud_get_plant_list():
    token = state.get("input_text.token")
    if not token:
        log.error("[PLANT LIST] ❌ Missing token")
        return

    appkey = pyscript.app_config["appkey"]
    access_key = pyscript.app_config["access_key"]
    rsa_key = pyscript.app_config["rsa_key"]

    url = "https://gateway.isolarcloud.eu/openapi/getPowerStationList"
    unenc_key = generate_random_key()
    encrypted_key = rsa_encrypt_secret_key(unenc_key, rsa_key)
    headers = build_headers(encrypted_key, access_key, token)
    body = build_encrypted_payload({"curPage": 1, "size": 10}, appkey, token, unenc_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=body) as response:
                raw = await response.text()
                decrypted = aes_decrypt(raw, unenc_key)
                plants = decrypted.get("result_data", {}).get("pageList", [])
                if plants:
                    ps_id = plants[0].get("ps_id")
                    state.set("sensor.plant_id", ps_id)
                    log.info(f"[PLANT LIST] 🌱 Stored ps_id: {ps_id}")
                else:
                    log.warning("[PLANT LIST] ⚠️ No plants found")
    except Exception as e:
        log.error(f"[PLANT LIST] ❌ Exception: {e}")

# ================================
# 🔌 GET DEVICE LIST
# ================================

@service
async def suncloud_get_device_list():
    token = state.get("input_text.token")
    ps_id = state.get("sensor.plant_id")
    if not token or not ps_id:
        log.error("[DEVICE LIST] ❌ Missing token or ps_id")
        return

    appkey = pyscript.app_config["appkey"]
    access_key = pyscript.app_config["access_key"]
    rsa_key = pyscript.app_config["rsa_key"]

    url = "https://gateway.isolarcloud.eu/openapi/getDeviceList"
    unenc_key = generate_random_key()
    encrypted_key = rsa_encrypt_secret_key(unenc_key, rsa_key)
    headers = build_headers(encrypted_key, access_key, token)
    body = build_encrypted_payload({"curPage": 1, "size": 50, "ps_id": ps_id}, appkey, token, unenc_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=body) as response:
                raw = await response.text()
                decrypted = aes_decrypt(raw, unenc_key)
                devices = decrypted.get("result_data", {}).get("pageList", [])
                for device in devices:
                    if device.get("device_type") == 22:
                        sn = device.get("device_sn") or device.get("communication_dev_sn")
                        if sn:
                            save_suncloud_config(sn=sn)
                            log.info(f"[DEVICE LIST] ✅ Stored SN: {sn}")
                            return
                log.warning("[DEVICE LIST] ⚠️ No type 22 module found")
    except Exception as e:
        log.error(f"[DEVICE LIST] ❌ Exception: {e}")

# ================================
# 🔍 GET PLANT INFO
# ================================

@service
async def suncloud_get_plant_info():
    token = state.get("input_text.token")
    sn = state.get("sensor.module_sn")  # <-- Set by get_device_list()
    if not token or not sn:
        log.error("[PLANT INFO] ❌ Missing token or SN")
        return

    appkey = pyscript.app_config["appkey"]
    access_key = pyscript.app_config["access_key"]
    rsa_key = pyscript.app_config["rsa_key"]

    url = "https://gateway.isolarcloud.eu/openapi/getPowerStationDetail"
    unenc_key = generate_random_key()
    encrypted_key = rsa_encrypt_secret_key(unenc_key, rsa_key)
    headers = build_headers(encrypted_key, access_key, token)

    payload = {
        "sn": sn,
        "is_get_ps_remarks": "1"
    }

    encrypted_body = build_encrypted_payload(payload, appkey, token, unenc_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=encrypted_body) as response:
                raw = await response.text()
                decrypted = aes_decrypt(raw, unenc_key)
                ps_key = decrypted.get("result_data", {}).get("ps_key", "")
                if ps_key:
                    save_suncloud_config(ps_key=ps_key)
                    state.set("input_text.ps_key", ps_key)
                    log.info(f"[PLANT INFO] 🔑 ps_key: {ps_key}")
                else:
                    log.warning("[PLANT INFO] ⚠️ No ps_key in response")
    except Exception as e:
        log.error(f"[PLANT INFO] ❌ Exception: {e}")

# ================================
# 📊 GET TELEMETRY POINTS
# ================================

@service
async def suncloud_get_suncloud_points():
    token = state.get("input_text.token")
    if not token:
        log.error("[POINTS] ❌ No token")
        return

    appkey = pyscript.app_config["appkey"]
    access_key = pyscript.app_config["access_key"]
    rsa_key = pyscript.app_config["rsa_key"]

    url = "https://gateway.isolarcloud.com/openapi/getOpenPointInfo"
    unenc_key = generate_random_key()
    encrypted_key = rsa_encrypt_secret_key(unenc_key, rsa_key)

    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "sys_code": "901",
        "x-access-key": access_key,                  # ✅ Must be plaintext
        "x-random-secret-key": encrypted_key,        # ✅ Encrypted AES key
        "token": token
    }
    log.info(f"[RSA] Encripting {unenc_key} with {rsa_key}")
    log.info(f"[HEA] Headers: {headers}")

    payload = {
        "appkey": appkey,
        "token": token,
        "lang": "_en_US",
        "api_key_param": {
            "nonce": generate_nonce(),
            "timestamp": str(int(time.time() * 1000))
        },
        "device_type": 11,
        "type": 2,
        "curPage": 1,
        "size": 999
    }
    log.info(f"[PAY] Payload: {payload}")

    encrypted_body = aes_encrypt(json.dumps(payload), unenc_key)
    log.info(f"[AES] Encrypted Body: {encrypted_body[:200]}...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=encrypted_body) as response:
                log.info(f"[HTTP] Status: {response.status}")
                raw = await response.text()
                log.info(f"[POINTS] 🔐 Raw Encrypted Response: {raw[:200]}...")

                decrypted = aes_decrypt(raw, unenc_key)
                log.info(f"[POINTS] 🧬 Decrypted: {decrypted if decrypted else '{}'}")
                log.info(f"[POINTS] ✅ result_code: {decrypted.get('result_code')}")

                telemetry_points = decrypted.get("result_data", {}).get("pageList", [])
                if not telemetry_points:
                    log.warning("[POINTS] ⚠️ No telemetry points returned")
                    return

                points = {}
                for point in telemetry_points:
                    pid = str(point.get("point_id"))
                    points[pid] = {
                        "name": point.get("point_name"),
                        "unit": point.get("storage_unit", "")
                    }

                save_suncloud_config(new_points=points)
                log.info(f"[POINTS] ✅ Saved {len(points)} telemetry points")

    except Exception as e:
        log.error(f"[POINTS] ❌ Exception: {e}")

# ================================
# 📶 GET REALTIME VALUES
# ================================

@service
async def suncloud_get_realtime_data():
    token = state.get("input_text.token")
    if not token:
        log.error("[REALTIME] ❌ Missing token")
        return

    appkey = pyscript.app_config["appkey"]
    access_key = pyscript.app_config["access_key"]
    rsa_key = pyscript.app_config["rsa_key"]
    config = load_suncloud_config()
    ps_key = config.get("ps_key")
    points = config.get("points", {})

    if not ps_key or not points:
        log.error("[REALTIME] ❌ Missing ps_key or points")
        return

    point_ids = list(points.keys())
    log.info(f"[REALTIME] 📡 Reading points: {point_ids}")

    url = "https://gateway.isolarcloud.com/openapi/getDeviceRealTimeData"
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))
    random_secret = generate_random_key()
    encrypted_key = rsa_encrypt_secret_key(random_secret, rsa_key)

    headers = build_headers(encrypted_key, access_key, token=token)

    payload = {
        "appkey": appkey,
        "token": token,
        "lang": "_en_US",
        "api_key_param": {"nonce": nonce, "timestamp": timestamp},
        "device_type": 11,
        "point_id_list": point_ids,
        "ps_key_list": [ps_key]
    }

    encrypted_body = aes_encrypt(json.dumps(payload), random_secret)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=encrypted_body) as response:
                raw = await response.text()
                decrypted = aes_decrypt(raw, random_secret)
                device_data = decrypted.get("result_data", {}).get("device_point_list", [{}])[0].get("device_point", {})
                if not device_data:
                    log.warning("[REALTIME] ⚠️ No device_point returned")
                    return
                for key, val in device_data.items():
                    if not key.startswith("p"):
                        continue
                    pid = key[1:]
                    meta = points.get(pid, {})
                    sensor_id = f"sensor.suncloud_{pid}"
                    state.set(sensor_id, val, {
                        "friendly_name": f"{pid}_{meta.get('name')}",
                        "unit_of_measurement": meta.get("unit"),
                        "icon": "mdi:chart-line",
                        "state_class": "measurement"
                    })
                log.info(f"[REALTIME] ✅ Updated {len(device_data)} sensors")
    except Exception as e:
        log.error(f"[REALTIME] ❌ Exception: {e}")
