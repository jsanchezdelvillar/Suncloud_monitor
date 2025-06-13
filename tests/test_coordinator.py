import json
import pytest
from unittest.mock import MagicMock

from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator


class DummyBus:
    async def async_listen_once(self, event, callback):
        """Simulate Home Assistant's bus.listen_once method."""
        return None


class DummyConfig:
    @staticmethod
    def path(name):
        return name


class DummyHass:
    def __init__(self):
        self.bus = DummyBus()
        self.config = DummyConfig()


def make_mock_entry(data=None, options=None):
    """Return a mock ConfigEntry with .data and .options as dicts."""
    mock_entry = MagicMock()
    mock_entry.data = data or {}
    mock_entry.options = options or {}
    return mock_entry


def test_coordinator_initializes():
    hass = DummyHass()
    entry = make_mock_entry()
    coordinator = SuncloudDataCoordinator(hass, entry)
    assert coordinator.hass is hass
    assert coordinator.config_entry.data == entry.data
    assert coordinator.points == {}


def test_rsa_encrypt_returns_string():
    coordinator = SuncloudDataCoordinator(DummyHass(), make_mock_entry())
    result = coordinator._rsa_encrypt("test", "invalidkey===")
    assert isinstance(result, str)


def test_aes_encrypt_and_decrypt_roundtrip():
    coordinator = SuncloudDataCoordinator(DummyHass(), make_mock_entry())
    secret = "secret-message"
    password = "password"
    secret_json = json.dumps({"msg": secret})
    encrypted_json = coordinator._aes_encrypt(secret_json, password)
    decrypted = coordinator._aes_decrypt(encrypted_json, password)
    assert isinstance(decrypted, dict)
    assert decrypted["msg"] == secret


def test_aes_decrypt_garbage_returns_none():
    coordinator = SuncloudDataCoordinator(DummyHass(), make_mock_entry())
    assert coordinator._aes_decrypt("nothex", "password") is None


def test_build_headers_without_token():
    entry = make_mock_entry(data={"access_key": "foo"})
    coordinator = SuncloudDataCoordinator(DummyHass(), entry)
    coordinator.config = entry.data
    headers = coordinator._build_headers("encryptedkey")
    assert "Content-Type" in headers
    assert headers["x-access-key"] == "foo"
    assert "token" not in headers


def test_build_headers_with_token():
    entry = make_mock_entry(data={"access_key": "foo"})
    coordinator = SuncloudDataCoordinator(DummyHass(), entry)
    coordinator.config = entry.data
    headers = coordinator._build_headers("encryptedkey", token="TOKEN")
    assert headers["token"] == "TOKEN"


@pytest.mark.asyncio
async def test_async_start_and_shutdown():
    """Test async_start registers a shutdown listener, and _on_shutdown removes it."""
    hass = DummyHass()
    entry = make_mock_entry()
    coordinator = SuncloudDataCoordinator(hass, entry)

    await coordinator.async_start()
    assert coordinator._unsub_stop is not None

    # Trigger shutdown
    await coordinator._on_shutdown(None)
    assert coordinator._unsub_stop is None
