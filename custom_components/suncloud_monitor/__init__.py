"""Suncloud Monitor integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Suncloud Monitor from config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = entry.data
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Suncloud Monitor config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop("config", None)
    return unload_ok
