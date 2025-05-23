"""Config flow for Suncloud Monitor."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_APPKEY,
    CONF_SECRET,
    CONF_RSA,
    CONF_BASE_URL,
    CONF_PS_KEY,
    CONF_POLL_INTERVAL,
)

DEFAULT_BASE_URL = "https://gateway.isolarcloud.eu"
DEFAULT_POLL_INTERVAL = 5

class SuncloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Suncloud Monitor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="Suncloud Monitor", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_APPKEY): str,
            vol.Required(CONF_SECRET): str,
            vol.Required(CONF_RSA): str,
            vol.Required(CONF_PS_KEY): str,
            vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
            vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow handler."""
        return SuncloudOptionsFlowHandler(config_entry)

class SuncloudOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Suncloud Monitor."""

    def __init__(self, config_entry):
        """Initialize SuncloudOptionsFlowHandler."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle the initial step of the options flow."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle the user step in the options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        schema = vol.Schema({
            vol.Optional(
                CONF_POLL_INTERVAL,
                default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            ): int
        })

        return self.async_show_form(step_id="user", data_schema=schema)
