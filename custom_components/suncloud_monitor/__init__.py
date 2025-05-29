from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import SuncloudDataCoordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (unused, but required)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Suncloud Monitor from a config entry."""
    coordinator = SuncloudDataCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    # Save the coordinator instance
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and cleanup."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_close()  # ✅ Properly close aiohttp session

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
