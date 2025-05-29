import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_POINTS

import yaml
from pathlib import Path


def load_points_from_yaml(hass):
    path = Path(hass.config.path("custom_components/suncloud_monitor/config_storage.yaml"))
    if path.exists():
        with open(path, "r") as f:
            return yaml.safe_load(f).get("points", {})
    return {}


class SuncloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Suncloud Monitor", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("appkey"): str,
                vol.Required("access_key"): str,
                vol.Required("rsa_key"): str,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SuncloudOptionsFlow(config_entry)


class SuncloudOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        points = load_points_from_yaml(self.hass)
        all_point_ids = sorted(points.keys())
        default_selected = self.config_entry.options.get(CONF_POINTS, all_point_ids)

        if user_input is not None:
            return self.async_create_entry(title="", data={
                CONF_POINTS: user_input[CONF_POINTS]
            })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_POINTS,
                    default=default_selected
                ): selector.selector({
                    "select": {
                        "multiple": True,
                        "options": all_point_ids,
                        "translation_key": "point_selector"
                    }
                })
            })
        )
