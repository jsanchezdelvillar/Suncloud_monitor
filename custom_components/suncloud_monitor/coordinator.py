import logging
import base64
import json
import random
import string
import time
from pathlib import Path
from datetime import timedelta
from typing import Any

import aiohttp
import yaml  # type: ignore
import aiofiles  # type: ignore

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONFIG_STORAGE_FILE,
    DEFAULT_SCAN_INTERVAL,
    CONF_ACCESS_KEY,
    CONF_APPKEY,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_RSA_KEY,
)

_LOGGER = logging.getLogger(__name__)


def generate_random_key(length: int = 16) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_nonce(length: int = 32) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class SuncloudDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict[Any, Any]):
        self.hass = hass
        self.config = config
        self.points: dict[str, dict[str, Any]] = {}
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
            _LOGGER.error("[CONFIG] ❌ Failed to load config: %s", e)

    async def _save_config_storage(self, selected_points=None):
        try:
            dump = yaml.dump(
                {
                    "points": selected_points or self.points,
                    "ps_key": self.ps_key,
                    "sn": self.sn,
                }
            )
            async with aiofiles.open(self.storage_path, "w") as f:
                await f.write(dump)
        except Exception as e:
            _LOGGER.error("[CONFIG] ❌ Save failed: %s", e)

    def _rsa_encrypt(self, secret: str, pubkey_b64: str) -> str:
        try:
            pubkey_bytes = base64.urlsafe_b64decode(pubkey_b64.strip())
            pubkey = serialization.load_der_public_key(
                pubkey_bytes, backend=default_backend()
            )
            if not isinstance(pubkey, RSAPublicKey):
                raise TypeError("Public key is not an RSA public key")
            encrypted = pubkey.encrypt(secret.encode(), rsa_padding.PKCS1v15())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            _LOGGER.error("[RSA] ❌ %s", e)
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
            _LOGGER.error("[AES] ❌ %s", e)
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
            _LOGGER.error("[AES] ❌ %s", e)
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
        payload.update(
            {
                "appkey": self.config[CONF_APPKEY],
                "token": token,
                "lang": "_en_US",
                "api_key_param": {
                    "nonce": generate_nonce(),
                    "timestamp": str(int(time.time() * 1000)),
                },
            }
        )
        _LOGGER.debug("[PAYLOAD] 🔓 %s", json.dumps(payload))
        encrypted = self._aes_encrypt(json.dumps(payload), unenc_key)
        _LOGGER.debug("[PAYLOAD] 🔐 %s...", encrypted[:200])
        return encrypted

    async def _authenticate(self):
        await self._load_config_storage()
        url = "https://gateway.isolarcloud.eu/openapi/login"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {
            "api_key_param": {
                "nonce": generate_nonce(),
                "timestamp": str(int(time.time() * 1000)),
            },
            "appkey": self.config[CONF_APPKEY],
            "login_type": "1",
            "user_account": self.config[CONF_USERNAME],
            "user_password": self.config[CONF_PASSWORD],
        }
        _LOGGER.debug("[LOGIN] 🔓 %s", json.dumps(payload))
        encrypted_body = self._aes_encrypt(json.dumps(payload), unenc_key)
        async with self.session.post(
            url, headers=self._build_headers(encrypted_key), data=encrypted_body
        ) as response:
            raw = await response.text()
            _LOGGER.debug("[LOGIN] 🔐 %s", raw[:500])
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug(
                "[LOGIN] 🔓 %s",
                json.dumps(decrypted, indent=2),
            )
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
        encrypted_payload = self._build_encrypted_payload(
            payload, self.token, unenc_key
        )
        async with self.session.post(
            url,
            headers=self._build_headers(encrypted_key, self.token),
            data=encrypted_payload,
        ) as response:
            raw = await response.text()
            _LOGGER.debug("[PS_ID] 🔐 %s", raw[:500])
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug("[PS_ID] 🔓 %s", json.dumps(decrypted, indent=2))
            result_data = decrypted.get("result_data")
            self.ps_id = result_data.get("pageList", [{}])[0].get("ps_id")

    async def _fetch_sn(self):
        url = "https://gateway.isolarcloud.eu/openapi/getDeviceList"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"curPage": 1, "size": 50, "ps_id": self.ps_id}
        encrypted_payload = self._build_encrypted_payload(
            payload, self.token, unenc_key
        )
        async with self.session.post(
            url,
            headers=self._build_headers(encrypted_key, self.token),
            data=encrypted_payload,
        ) as response:
            raw = await response.text()
            _LOGGER.debug("[SN] 🔐 %s", raw[:500])
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug("[SN] 🔓 %s", json.dumps(decrypted, indent=2))
            result_data = decrypted.get("result_data")
            page_list = result_data.get("pageList", [])
            comm_sn = None
            # Find the communication module and use its communication_dev_sn

            for device in page_list:
                comm_sn = device.get("communication_dev_sn")
                # Make sure it's not null and device type is 'Communication module'

                type_name = device.get("type_name", "").lower()
                if comm_sn and type_name == "communication module":
                    break
            self.sn = comm_sn

    async def _fetch_ps_key(self):
        url = "https://gateway.isolarcloud.eu/openapi/getPowerStationDetail"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"sn": self.sn, "is_get_ps_remarks": "1"}
        encrypted_payload = self._build_encrypted_payload(
            payload, self.token, unenc_key
        )
        async with self.session.post(
            url,
            headers=self._build_headers(encrypted_key, self.token),
            data=encrypted_payload,
        ) as response:
            raw = await response.text()
            _LOGGER.debug("[PS_KEY] 🔐 %s", raw[:500])
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug("[PS_KEY] 🔓 %s", json.dumps(decrypted, indent=2))
            result_data = decrypted.get("result_data")
            self.ps_key = result_data.get("ps_key")

    async def _fetch_points(self):
        url = "https://gateway.isolarcloud.eu/openapi/getOpenPointInfo"
        unenc_key = generate_random_key()
        encrypted_key = self._rsa_encrypt(unenc_key, self.config[CONF_RSA_KEY])
        payload = {"device_type": 11, "type": 2, "curPage": 1, "size": 999}
        encrypted_payload = self._build_encrypted_payload(
            payload, self.token, unenc_key
        )
        async with self.session.post(
            url,
            headers=self._build_headers(encrypted_key, self.token),
            data=encrypted_payload,
        ) as response:
            raw = await response.text()
            _LOGGER.debug("[POINTS] 🔐 %s", raw[:500])
            decrypted = self._aes_decrypt(raw, unenc_key)
            _LOGGER.debug("[POINTS] 🔓 %s", json.dumps(decrypted, indent=2))
            result_data = decrypted.get("result_data")

            if isinstance(result_data, dict):
                points_list = result_data.get("pageList", [])
            elif isinstance(result_data, list):
                points_list = result_data
            else:
                points_list = []
            self.points = {
                str(point.get("id", point.get("point_id"))): point
                for point in points_list
            }
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
                "ps_key_list": [self.ps_key],
            }
            encrypted_payload = self._build_encrypted_payload(
                payload, self.token, unenc_key
            )
            async with self.session.post(
                url,
                headers=self._build_headers(encrypted_key, self.token),
                data=encrypted_payload,
            ) as response:
                raw = await response.text()
                _LOGGER.debug("[REALTIME] 🔐 %s", raw[:500])
                decrypted = self._aes_decrypt(raw, unenc_key)
                _LOGGER.debug("[REALTIME] 🔓 %s", json.dumps(decrypted, indent=2))
                if not decrypted or not isinstance(decrypted, dict):
                    raise UpdateFailed("[REALTIME] ❌ Decryption failed")
                result_data = decrypted.get("result_data")
                if not result_data:
                    raise UpdateFailed("[REALTIME] ❌ Missing result_data")
                device_list = result_data.get("device_point_list", [])
                device_data = (
                    device_list[0].get("device_point", {}) if device_list else {}
                )
                parsed = {
                    key[1:]: val
                    for key, val in device_data.items()
                    if key.startswith("p")
                }
                _LOGGER.info("[REALTIME] ✅ %d points updated", len(parsed))
                return parsed
        except Exception as e:
            raise UpdateFailed(f"[REALTIME] ❌ Exception: {e}")

    async def async_close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @callback
    async def _on_shutdown(self, _event):
        await self.async_close()

    # ----------------- ADDED: Remove orphaned sensors -----------------

    async def remove_orphaned_sensors(self):
        """
        Remove sensors that do not belong to the current points list.
        Must be called after points list is updated.
        """

        from homeassistant.helpers.entity_registry import (
            async_get as async_get_entity_registry,
        )

        entity_registry = async_get_entity_registry(self.hass)
        current_point_ids = set(self.points.keys())
        entity_prefix = "sensor.suncloud_"

        for entity in list(entity_registry.entities.values()):
            if (
                entity.platform == "suncloud_monitor"
                and entity.entity_id.startswith(entity_prefix)
                and entity.unique_id.replace("suncloud_", "") not in current_point_ids
            ):
                entity_registry.async_remove(entity.entity_id)
