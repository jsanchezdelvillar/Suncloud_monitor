"""Basic integration test for Suncloud Monitor."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

DOMAIN = "suncloud_monitor"

@pytest.mark.asyncio
async def test_setup_and_teardown(hass: HomeAssistant):
    """Test setting up the integration with minimal config."""
    assert await async_setup_component(hass, {
        DOMAIN: {
            "username": "demo",
            "password": "demo",
            "base_url": "https://example.com"
        }
    }, DOMAIN)
    await hass.async_block_till_done()

    assert DOMAIN in hass.config.components
