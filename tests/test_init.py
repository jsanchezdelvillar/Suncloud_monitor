import pytest
from custom_components.suncloud_monitor import async_setup_entry, async_unload_entry


class DummyEntry:
    def __init__(self, entry_id, data):
        self.entry_id = entry_id
        self.data = data


class DummyConfigEntries:
    async def async_forward_entry_setups(self, entry, platforms):
        return True

    async def async_unload_platforms(self, entry, platforms):
        return True


class DummyConfig:
    def __init__(self):
        self.config_dir = "/tmp"  # or any directory you want to use for testing

    def path(self, filename):
        # You can keep this as returning just the filename, but for more realistic behavior:
        return f"{self.config_dir}/{filename}"


class DummyBus:
    async def async_listen_once(self, event, callback):
        pass  # Do nothing for the test


class DummyHass:
    def __init__(self):
        self.data = {}
        self.config = DummyConfig()
        self.config_entries = DummyConfigEntries()
        self.bus = DummyBus()


@pytest.mark.asyncio
async def test_async_setup_entry_adds_coordinator(monkeypatch):
    from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator

    async def dummy_refresh(self):
        pass

    monkeypatch.setattr(
        SuncloudDataCoordinator, "async_config_entry_first_refresh", dummy_refresh
    )

    hass = DummyHass()
    entry = DummyEntry("id123", {})
    result = await async_setup_entry(hass, entry)
    assert result is True
    assert "id123" in hass.data["suncloud_monitor"]


@pytest.mark.asyncio
async def test_async_unload_entry_removes_coordinator(monkeypatch):
    from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator

    async def dummy_close(self):
        pass

    monkeypatch.setattr(SuncloudDataCoordinator, "async_close", dummy_close)

    hass = DummyHass()
    entry = DummyEntry("id123", {})
    hass.data["suncloud_monitor"] = {"id123": SuncloudDataCoordinator(hass, {})}
    result = await async_unload_entry(hass, entry)
    assert result is True
    assert "id123" not in hass.data["suncloud_monitor"]
