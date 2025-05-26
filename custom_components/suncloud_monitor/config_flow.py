import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class SuncloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Suncloud Monitor."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Save the config entry
            return self.async_create_entry(title="Suncloud Monitor", data=user_input)

        schema = vol.Schema({
            vol.Required("suncloud_username"): str,
            vol.Required("suncloud_password"): str,
            vol.Required("suncloud_appkey"): str,
            vol.Required("suncloud_secret"): str,
            vol.Required("suncloud_rsa_key"): str,
            vol.Optional("ps_key", default=""): str,
            vol.Optional("base_url", default="https://gateway.isolarcloud.eu"): str,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

