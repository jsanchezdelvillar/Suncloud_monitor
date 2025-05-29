from __future__ import annotations

import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_APPKEY,
    CONF_ACCESS_KEY,
    CONF_RSA_KEY,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_POINTS,
)

class SuncloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SunCloud Monitor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """First step: gather credentials."""
        if user_input is not None:
            return self.async_create_entry(title="SunCloud Monitor", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_APPKEY): str,
                vol.Required(CONF_ACCESS_KEY): str,
                vol.Required(CONF_RSA_KEY): str,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return SuncloudOptionsFlow(entry)


class SuncloudOptionsFlow(config_entries.OptionsFlow):
    """Handle options for existing config."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Let the user choose which telemetry points to enable."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Dummy point IDs for now (will be dynamically populated later from config_storage.yaml)
        all_points = self.hass.data[DOMAIN][self.entry.entry_id].points
        options = {pid: f"{pid} - {meta['name']}" for pid, meta in all_points.items()}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_POINTS, default=list(all_points.keys())): vol.All(vol.EnsureList(), [vol.In(list(all_points.keys()))]),
            }),
        )
