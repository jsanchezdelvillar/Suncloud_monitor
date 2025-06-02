import pytest
from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator
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


def test_coordinator_initializes():
    hass = DummyHass()
    config = {"some": "value"}
    coordinator = SuncloudDataCoordinator(hass, config)
    assert coordinator.hass is hass
    assert coordinator.config == config
    assert coordinator.points == {}


def test_rsa_encrypt_returns_string():
    coordinator = SuncloudDataCoordinator(DummyHass(), {})
    result = coordinator._rsa_encrypt("test", "invalidkey===")
    assert isinstance(result, str)


def test_aes_encrypt_and_decrypt_roundtrip():
    coordinator = SuncloudDataCoordinator(DummyHass(), {})
    secret = "secret-message"
    password = "password"
    encrypted = coordinator._aes_encrypt(secret, password)
    # _aes_decrypt expects hex and returns JSON, so use a JSON string
    secret_json = json.dumps({"msg": secret})
    encrypted_json = coordinator._aes_encrypt(secret_json, password)
    decrypted = coordinator._aes_decrypt(encrypted_json, password)
    assert isinstance(decrypted, dict)
    assert decrypted["msg"] == secret


def test_aes_decrypt_garbage_returns_none():
    coordinator = SuncloudDataCoordinator(DummyHass(), {})
    assert coordinator._aes_decrypt("nothex", "password") is None


def test_build_headers_without_token():
    coordinator = SuncloudDataCoordinator(DummyHass(), {"access_key": "foo"})
    headers = coordinator._build_headers("encryptedkey")
    assert "Content-Type" in headers
    assert headers["x-access-key"] == "foo"
    assert "token" not in headers


def test_build_headers_with_token():
    coordinator = SuncloudDataCoordinator(DummyHass(), {"access_key": "foo"})
    headers = coordinator._build_headers("encryptedkey", token="TOKEN")
    assert headers["token"] == "TOKEN"
