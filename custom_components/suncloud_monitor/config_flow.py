from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class SunCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for SunCloud Monitor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="SunCloud Monitor", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("base_url", default="https://your-api-url.com"): str,
                vol.Optional("poll_interval", default=5): vol.All(int, vol.Range(min=1, max=60))
            })
        )
