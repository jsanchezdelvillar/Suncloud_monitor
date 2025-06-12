from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator
from unittest.mock import MagicMock
import json


class DummyHass:
    class config:
        @staticmethod
        def path(name):
            return name

    class bus:
        @staticmethod
        def async_listen_once(event, callback):
            pass


def make_mock_entry(data=None, options=None):
    mock_entry = MagicMock()
    mock_entry.data = data or {}
    mock_entry.options = options or {}
    return mock_entry


def test_coordinator_initializes():
    hass = DummyHass()
    entry = make_mock_entry()
    coordinator = SuncloudDataCoordinator(hass, entry)
    assert coordinator.hass is hass
    assert coordinator.config_entry == entry
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
