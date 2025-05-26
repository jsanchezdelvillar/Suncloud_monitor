import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity

from .api import post_request
from .const import DOMAIN, REALTIME_ENDPOINT, TOKEN_KEY, PS_KEY_STATE, TELEMETRY_SELECT

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    config = hass.data[DOMAIN]["config"]
    coordinator = SuncloudCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    telemetry_ids = hass.states.get(TELEMETRY_SELECT)
    points = telemetry_ids.attributes.get("options", []) if telemetry_ids else []

    sensors = []
    for pid in points:
        sensors.append(SuncloudSensor(coordinator, pid))
    async_add_entities(sensors)


class SuncloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict):
        self.hass = hass
        self.config = config
        super().__init__(
            hass,
            _LOGGER,
            name="Suncloud Monitor Coordinator",
            update_interval=SCAN_INTERVAL
        )

    async def _async_update_data(self):
        token = hass.states.get(TOKEN_KEY).state
        ps_key = hass.states.get(PS_KEY_STATE).state

        if not token or token in ["none", "Error", "unavailable"]:
            _LOGGER.warning("Token not set or invalid, skipping update.")
            return {}

        if not ps_key or ps_key == "none":
            _LOGGER.warning("PS Key not available. Triggering auto-recovery.")
            hass.async_create_task(hass.services.async_call("pyscript", "get_plant_info"))
            return {}

        telemetry_select = self.hass.states.get(TELEMETRY_SELECT)
        point_ids = telemetry_select.attributes.get("options", []) if telemetry_select else []

        if not point_ids:
            _LOGGER.warning("No telemetry points configured.")
            return {}

        payload = {
            "device_type": 11,
            "point_id_list": point_ids,
            "ps_key_list": [ps_key]
        }

        result = await post_request(REALTIME_ENDPOINT, payload, self.config, token=token)

        if not result or result.get("result_code") != "1":
            _LOGGER.warning("API failed or bad result, will retry recovery.")
            return {}

        return result.get("result_data", {}).get("device_point_list", [{}])[0].get("device_point", {})


class SuncloudSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator: SuncloudCoordinator, point_id: str):
        super().__init__(coordinator)
        self._point_id = point_id
        self._attr_unique_id = f"suncloud_{point_id}"
        self._attr_name = f"Suncloud {point_id}"
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self):
        return self.coordinator.data.get(f"p{self._point_id}", "unavailable")
