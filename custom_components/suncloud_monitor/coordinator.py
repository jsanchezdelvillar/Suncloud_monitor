import logging
import base64
import json
import random
import string
import time
from pathlib import Path
from datetime import timedelta

import aiohttp
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import *

_LOGGER = logging.getLogger(__name__)

def generate_random_key(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class SuncloudDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict):
        self.hass = hass
        self.config = config
        self.points = {}
        self.token = None
        self.ps_id = None
        self.sn = None
        self.ps_key = None
        self.session = aiohttp.ClientSession()
        self.storage_path = Path(hass.config.path(CONFIG_STORAGE_FILE))
        self._load_config_storage()

        super().__init__(
            hass,
            _LOGGER,
            name="SunCloud Monitor",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def _load_config_storage(self):
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                    self.points = data.get("points", {})
                    self.ps_key = data.get("ps_key")
                    self.sn = data.get("sn")
                    _LOGGER.debug(f"[CONFIG] Loaded {len(self.points)} points")
        except Exception as e:
            _LOGGER.error(f"[CONFIG] ❌ Failed to load config: {e}")

    def _save_config_storage(self):
        try:
            with open(self.storage_path, "w") as f:
                yaml.dump({
                    "points": self.points,
                    "ps_key": self.ps_key,
                    "sn": self.sn
                }, f)
        except Exception as e:
            _LOGGER.error(f"[CONFIG] ❌ Save failed: {e}")

    def _rsa_encrypt(self, secret: str, pubkey_b64: str) -> str:
        try:
            pubkey_bytes = base64.urlsafe_b64decode(pubkey_b64.strip())
            pubkey = serialization.load_der_public_key(pubkey_bytes, backend=default_backend())
            encrypted = pubkey.encrypt(secret.encode(), rsa_padding.PKCS1v15())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            _LOGGER.error(f"[RSA] ❌ {e}")
            return ""

    def _aes_encrypt(self, content: str, password: str) -> str:
        try:
            key = password.encode().ljust(16)[:16]
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
            padder = PKCS7(128).padder()
            padded = padder.update(content.encode()) + padder.finalize()
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded) + encryptor.finalize()
            return encrypted.hex().upper()
        except Exception as e:
            _LOGGER.error(f"[AES] ❌ {e}")
            return ""

    def _aes_decrypt(self, content: str, password: str):
        try:
            key = password.encode().ljust(16)[:16]
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(bytes.fromhex(content)) + decryptor.finalize()
            unpadder = PKCS7(128).unpadder()
            unpadded = unpadder.update(decrypted) + unpadder.finalize()
            return json.loads(unpadded.decode())
        except Exception as e:
            _LOGGER.error(f"[AES] ❌ {e}")
            return None

    def _build_headers(self, encrypted_key, token=None):
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "sys_code": "901",
            "x-access-key": self.config[CONF_ACCESS_KEY],
            "x-random-secret-key": encrypted_key,
        }
        if token:
            headers["token"] = token
        return headers

    def _build_encrypted_payload(self, payload: dict, token: str, unenc_key: str):
        payload.update({
            "appkey": self.config[CONF_APPKEY],
            "token": token,
            "lang": "_en_US",
            "api_key_param": {
                "nonce": generate_nonce(),
                "timestamp": str(int(time.time() * 1000))
            }
        })
        return self._aes_encrypt(json.dumps(payload), unenc_key)

    async def _authenticate(self):
        url = "https://gateway.isolarcloud.eu/openapi/login"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {
            "api_key_param": {
                "nonce": generate_random_key(),
                "timestamp": str(int(time.time() * 1000))
            },
            "appkey": self.config[CONF_APPKEY],
            "login_type": "1",
            "user_account": self.config[CONF_USERNAME],
            "user_password": self.config[CONF_PASSWORD]
        }
        encrypted_body = self._aes_encrypt(json.dumps(payload), unenc_key)
        async with self.session.post(url, headers=self._build_headers(encrypted_key), data=encrypted_body) as response:
            raw = await response.text()
            decrypted = self._aes_decrypt(raw, unenc_key)
            if not decrypted or not isinstance(decrypted, dict):
                raise UpdateFailed("[AUTH] ❌ Decryption failed")
            self.token = decrypted.get("result_data", {}).get("token")
            if not self.token:
                raise UpdateFailed("[AUTH] ❌ Failed to get token")

    # Other methods (_fetch_ps_id, _fetch_sn, _fetch_ps_key, _fetch_points) stay unchanged

    async def _async_update_data(self):
        try:
            await self._ensure_ready()

            point_ids = list(self.points.keys())
            url = "https://gateway.isolarcloud.eu/openapi/getDeviceRealTimeData"
            nonce = generate_random_key()
            timestamp = str(int(time.time() * 1000))
            unenc_key = generate_random_key()
            encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
            payload = self._build_encrypted_payload({
                "device_type": 11,
                "point_id_list": point_ids,
                "ps_key_list": [self.ps_key]
            }, self.token, unenc_key)
            async with self.session.post(url, headers=self._build_headers(encrypted_key, self.token), data=payload) as response:
                raw = await response.text()
                decrypted = self._aes_decrypt(raw, unenc_key)
                if not decrypted or not isinstance(decrypted, dict):
                    raise UpdateFailed("[REALTIME] ❌ Decryption failed")

                result_data = decrypted.get("result_data")
                if not result_data or not isinstance(result_data, dict):
                    raise UpdateFailed("[REALTIME] ❌ Missing or invalid result_data")

                device_list = result_data.get("device_point_list", [])
                if not device_list or not isinstance(device_list, list) or not device_list[0]:
                    raise UpdateFailed("[REALTIME] ❌ device_point_list missing or invalid")

                device_data = device_list[0].get("device_point", {})
                if not device_data:
                    raise UpdateFailed("[REALTIME] ⚠️ No telemetry returned")

                parsed = {}
                for key, val in device_data.items():
                    pid = key[1:]  # remove leading 'p'
                    parsed[pid] = val
                _LOGGER.info(f"[REALTIME] ✅ {len(parsed)} points updated")
                return parsed
        except Exception as e:
            raise UpdateFailed(f"[REALTIME] ❌ Exception: {e}")

    async def async_close(self):
        if self.session and not self.session.closed:
            await self.session.close()
