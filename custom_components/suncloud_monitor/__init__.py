"""SunCloud Monitor integration init."""
DOMAIN = "suncloud_monitor"

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = entry.data
    return True

async def async_unload_entry(hass, entry):
    return True
