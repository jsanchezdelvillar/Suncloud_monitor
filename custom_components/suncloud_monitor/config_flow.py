import voluptuous as vol
import yaml
import aiofiles
from pathlib import Path

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import DOMAIN, CONF_POINTS

async def load_points_from_yaml(hass):
    path = Path(
        hass.config.path("custom_components/suncloud_monitor/config_storage.yaml")
    )
    if path.exists():
        async with aiofiles.open(path, "r") as f:
            raw = await f.read()
        try:
            data = yaml.safe_load(raw)
            return data.get("points", {}) if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

async def save_points_to_yaml(hass, selected_points):
    """Save the filtered points list to config_storage.yaml, preserving other fields."""
    path = Path(
        hass.config.path("custom_components/suncloud_monitor/config_storage.yaml")
    )
    data = {}
    if path.exists():
        async with aiofiles.open(path, "r") as f:
            raw = await f.read()
            try:
                data = yaml.safe_load(raw)
            except Exception:
                data = {}
    data["points"] = selected_points
    async with aiofiles.open(path, "w") as f:
        await f.write(yaml.dump(data))

class SuncloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Suncloud Monitor", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("appkey"): str,
                    vol.Required("access_key"): str,
                    vol.Required("rsa_key"): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SuncloudOptionsFlow(config_entry)

class SuncloudOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        super().__init__()
        self._entry = entry

    async def async_step_init(self, user_input=None):
        points = await load_points_from_yaml(self.hass)
        all_point_ids = sorted(points.keys())
        default_selected = self._entry.options.get(CONF_POINTS, all_point_ids)

        if user_input is not None and user_input.get("repopulate"):
            return await self.async_step_repopulate()

        if user_input is not None and CONF_POINTS in user_input:
            selected_points = {pid: points[pid] for pid in user_input[CONF_POINTS]}
            await save_points_to_yaml(self.hass, selected_points)
            await self.hass.config_entries.async_reload(self._entry.entry_id)
            return self.async_create_entry(
                title="", data={CONF_POINTS: user_input[CONF_POINTS]}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_POINTS, default=default_selected): SelectSelector(
                        SelectSelectorConfig(
                            options=all_point_ids,
                            multiple=True,
                            translation_key="point_selector",
                        )
                    ),
                    vol.Optional("repopulate", default=False): bool,
                }
            ),
        )

    async def async_step_repopulate(self, user_input=None):
        coordinator = self.hass.data[DOMAIN][self._entry.entry_id]
        # Only fetch new points using the cached credentials/info
        await coordinator._fetch_points()
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        return await self.async_step_init()
