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
import aiofiles

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from homeassistant.core import HomeAssistant, callback
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
        self._session = None
        self.storage_path = Path(hass.config.path(CONFIG_STORAGE_FILE))
        super().__init__(
            hass,
            _LOGGER,
            name="SunCloud Monitor",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        hass.bus.async_listen_once("homeassistant_stop", self._on_shutdown)

    @property
    def session(self):
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _load_config_storage(self):
        try:
            if self.storage_path.exists():
                async with aiofiles.open(self.storage_path, "r") as f:
                    raw = await f.read()
                    data = yaml.safe_load(raw) or {}
                    self.points = data.get("points", {})
                    self.ps_key = data.get("ps_key")
                    self.sn = data.get("sn")
        except Exception as e:
            _LOGGER.error(f"[CONFIG] ❌ Failed to load config: {e}")

    async def _save_config_storage(self, selected_points=None):
        try:
            dump = yaml.dump({
                "points": selected_points or self.points,
                "ps_key": self.ps_key,
                "sn": self.sn
            })
            async with aiofiles.open(self.storage_path, "w") as f:
                await f.write(dump)
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
        _LOGGER.debug(f"[PAYLOAD] 🔓 {json.dumps(payload)}")
        encrypted = self._aes_encrypt(json.dumps(payload), unenc_key)
        _LOGGER.debug(f"[PAYLOAD] 🔐 {encrypted[:200]}...")
        return encrypted
    async def _authenticate(self):
        await self._load_config_storage()
        url = "https://gateway.isolarcloud.eu/openapi/login"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {
            "api_key_param": {
                "nonce": generate_nonce(),
                "timestamp": str(int(time.time() * 1000))
            },
            "appkey": self.config[CONF_APPKEY],
            "login_type": "1",
            "user_account": self.config[CONF_USERNAME],
            "user_password": self.config[CONF_PASSWORD]
        }
        _LOGGER.debug(f"[LOGIN] 🔓 {json.dumps(payload)}")
        encrypted_body = self._aes_encrypt(json.dumps(payload), unenc_key)
        async with self.session.post(url, headers=self._build_headers(encrypted_key), data=encrypted_body) as response:
            raw = await response.text()
            _LOGGER.debug(f"[LOGIN] 🔐 {raw[:500]}")
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug(f"[LOGIN] 🔓 {json.dumps(decrypted, indent=2)}")
            if not decrypted or not isinstance(decrypted, dict):
                raise UpdateFailed("[AUTH] ❌ Decryption failed")
            self.token = decrypted.get("result_data", {}).get("token")
            if not self.token:
                raise UpdateFailed("[AUTH] ❌ Missing token")

    async def _ensure_ready(self):
        if not self.token:
            await self._authenticate()
        if not self.ps_id:
            await self._fetch_ps_id()
        if not self.sn:
            await self._fetch_sn()
        if not self.ps_key:
            await self._fetch_ps_key()
        if not self.points:
            await self._fetch_points()
    async def _fetch_ps_id(self):
        url = "https://gateway.isolarcloud.eu/openapi/getPowerStationList"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"curPage": 1, "size": 1}
        encrypted_payload = self._build_encrypted_payload(payload, self.token, unenc_key)
        async with self.session.post(url, headers=self._build_headers(encrypted_key, self.token), data=encrypted_payload) as response:
            raw = await response.text()
            _LOGGER.debug(f"[PS_ID] 🔐 {raw[:500]}")
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug(f"[PS_ID] 🔓 {json.dumps(decrypted, indent=2)}")
            result_data = decrypted.get("result_data")
            self.ps_id = result_data.get("pageList", [{}])[0].get("ps_id")

    async def _fetch_sn(self):
        url = "https://gateway.isolarcloud.eu/openapi/getDeviceList"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"curPage": 1, "size": 50, "ps_id": self.ps_id}
        encrypted_payload = self._build_encrypted_payload(payload, self.token, unenc_key)
        async with self.session.post(url, headers=self._build_headers(encrypted_key, self.token), data=encrypted_payload) as response:
            raw = await response.text()
            _LOGGER.debug(f"[SN] 🔐 {raw[:500]}")
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug(f"[SN] 🔓 {json.dumps(decrypted, indent=2)}")
            result_data = decrypted.get("result_data")
            self.sn = result_data.get("pageList", [{}])[0].get("sn")

    async def _fetch_ps_key(self):
        url = "https://gateway.isolarcloud.eu/openapi/getPowerStationKey"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"ps_id": self.ps_id}
        encrypted_payload = self._build_encrypted_payload(payload, self.token, unenc_key)
        async with self.session.post(url, headers=self._build_headers(encrypted_key, self.token), data=encrypted_payload) as response:
            raw = await response.text()
            _LOGGER.debug(f"[PS_KEY] 🔐 {raw[:500]}")
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug(f"[PS_KEY] 🔓 {json.dumps(decrypted, indent=2)}")
            result_data = decrypted.get("result_data")
            self.ps_key = result_data.get("ps_key")
    async def _fetch_points(self):
        url = "https://gateway.isolarcloud.eu/openapi/getTelemetryPointList"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"ps_id": self.ps_id}
        encrypted_payload = self._build_encrypted_payload(payload, self.token, unenc_key)
        async with self.session.post(url, headers=self._build_headers(encrypted_key, self.token), data=encrypted_payload) as response:
            raw = await response.text()
            _LOGGER.debug(f"[POINTS] 🔐 {raw[:500]}")
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug(f"[POINTS] 🔓 {json.dumps(decrypted, indent=2)}")
            result_data = decrypted.get("result_data", [])
            self.points = {str(point["id"]): point for point in result_data}
            await self._save_config_storage()

    async def _async_update_data(self):
        try:
            await self._ensure_ready()
            point_ids = list(self.points.keys())
            url = "https://gateway.isolarcloud.eu/openapi/getDeviceRealTimeData"
            unenc_key = generate_random_key()
            encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
            payload = {
                "device_type": 11,
                "point_id_list": point_ids,
                "ps_key_list": [self.ps_key]
            }
            encrypted_payload = self._build_encrypted_payload(payload, self.token, unenc_key)
            async with self.session.post(url, headers=self._build_headers(encrypted_key, self.token), data=encrypted_payload) as response:
                raw = await response.text()
                _LOGGER.debug(f"[REALTIME] 🔐 {raw[:500]}")
                decrypted = self._aes_decrypt(raw, unenc_key)
                _LOGGER.debug(f"[REALTIME] 🔓 {json.dumps(decrypted, indent=2)}")
                if not decrypted or not isinstance(decrypted, dict):
                    raise UpdateFailed("[REALTIME] ❌ Decryption failed")
                result_data = decrypted.get("result_data")
                if not result_data:
                    raise UpdateFailed("[REALTIME] ❌ Missing result_data")
                device_list = result_data.get("device_point_list", [])
                device_data = device_list[0].get("device_point", {}) if device_list else {}
                parsed = {
                    key[1:]: val for key, val in device_data.items() if key.startswith("p")
                }
                _LOGGER.info(f"[REALTIME] ✅ {len(parsed)} points updated")
                return parsed
        except Exception as e:
            raise UpdateFailed(f"[REALTIME] ❌ Exception: {e}")

    async def async_close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @callback
    async def _on_shutdown(self, _event):
        await self.async_close()
