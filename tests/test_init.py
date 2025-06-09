import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.suncloud_monitor import async_setup_entry
from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator
from homeassistant.helpers import entity_registry as er


class DummyEntry:
    def __init__(self, entry_id, data):
        self.entry_id = entry_id
        self.data = data
        self.title = "Dummy Title"
        self.domain = "suncloud_monitor"
        self.options = {}
        self.pref_disable_new_entities = False
        self.pref_disable_polling = False
        self.unique_id = "dummy_unique_id"
        self.version = 1


class DummyBus:
    def async_listen(self, event_type, listener):
        return None

    async def async_listen_once(self, event_type, listener):
        return None


class DummyHass:
    def __init__(self):
        self.data = {}
        self.config_entries = DummyConfigEntries()
        self.bus = DummyBus()
        self.states = {}
        self.services = DummyServices()

    def async_create_task(self, coro):
        pass


class DummyConfigEntries:
    def async_setup_platforms(self, entry, platforms):
        return True

    async def async_forward_entry_setups(self, entry, platforms):
        return True

    async def async_unload_platforms(self, entry, platforms):
        return True


class DummyServices:
    def async_register(self, domain, service, handler, schema=None):
        pass


@pytest.mark.asyncio
async def test_async_setup_entry_adds_coordinator(monkeypatch):
    """Test async_setup_entry correctly adds coordinator."""

    async def dummy_refresh(self):
        pass

    monkeypatch.setattr(
        SuncloudDataCoordinator,
        "async_config_entry_first_refresh",
        dummy_refresh,
    )

    fake_registry = MagicMock()
    fake_registry.entities = {
        "sensor.suncloud_123": MagicMock(entity_id="sensor.suncloud_123")
    }
    fake_registry.async_remove = AsyncMock()

    monkeypatch.setattr(er, "async_get", lambda hass: fake_registry)

    hass = DummyHass()
    entry = DummyEntry("id123", {})

    result = await async_setup_entry(hass, entry)

    assert result is True
