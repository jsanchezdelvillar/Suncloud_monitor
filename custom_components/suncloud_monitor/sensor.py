from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers.entity import Entity
from datetime import timedelta
import logging

from .const import DOMAIN
from .api import post_request

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)

SENSOR_DEFINITIONS = {
    "83022": {"name": "Daily Yield", "unit": "Wh", "device_class": "energy", "icon": "mdi:transmission-tower", "state_class": "total_increasing"},
    "83033": {"name": "Current Power", "unit": "W", "device_class": "power", "icon": "mdi:flash", "state_class": "measurement"},
    "83025": {"name": "Equivalent Hours", "unit": "h", "icon": "mdi:clock", "state_class": "measurement"},
    "83102": {"name": "Energy Purchased", "unit": "Wh", "device_class": "energy", "icon": "mdi:transmission-tower", "state_class": "total_increasing"},
    "83072": {"name": "Energy Fed In", "unit": "Wh", "device_class": "energy", "icon": "mdi:transmission-tower-export", "state_class": "total_increasing"},
    "83106": {"name": "Load Power", "unit": "W", "device_class": "power", "icon": "mdi:lightning-bolt", "state_class": "measurement"}
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    config = hass.data[DOMAIN]["config"]
    coordinator = SuncloudCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    sensors = []
    for point_id, details in SENSOR_DEFINITIONS.items():
        sensors.append(SuncloudSensor(coordinator, point_id, details))
    async_add_entities(sensors)


class SuncloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict):
        self.hass = hass
        self.config = config
        self.token = config.get("token")
        super().__init__(
            hass,
            _LOGGER,
            name="Suncloud Monitor Coordinator",
            update_interval=SCAN_INTERVAL
        )

    async def _async_update_data(self):
        payload = {
            "device_type": 11,
            "point_id_list": list(SENSOR_DEFINITIONS.keys()),
            "ps_key_list": [self.config["ps_key"]],
            "appkey": self.config["appkey"]
        }
        data = await post_request(self.hass, self.config, "/openapi/getDeviceRealTimeData", payload, token=self.token)
        if not data or data.get("result_code") != "1":
            _LOGGER.warning("Failed to fetch device data")
            return {}
        return data.get("result_data", {}).get("device_point_list", [{}])[0].get("device_point", {})


class SuncloudSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator: SuncloudCoordinator, point_id: str, details: dict):
        super().__init__(coordinator)
        self._attr_unique_id = f"suncloud_{point_id}"
        self._attr_name = f"Suncloud {details['name']}"
        self._point_id = point_id
        self._attr_native_unit_of_measurement = details.get("unit")
        self._attr_icon = details.get("icon")
        self._attr_device_class = details.get("device_class")
        self._attr_state_class = details.get("state_class")

    @property
    def native_value(self):
        return self.coordinator.data.get(f"p{self._point_id}", "Unknown")

