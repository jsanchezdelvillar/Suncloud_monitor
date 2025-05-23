from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

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


async def async_setup_platform(hass: HomeAssistant, config: ConfigType, async_add_entities: AddEntitiesCallback, discovery_info=None):
    coordinator = SuncloudCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    sensors = []
    for point_id, details in SENSOR_DEFINITIONS.items():
        sensors.append(SuncloudSensor(coordinator, point_id, details))
    async_add_entities(sensors, True)


class SuncloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.config = hass.data[DOMAIN]["config"]
        self.token = hass.data[DOMAIN].get("token")
        super().__init__(
            hass,
            _LOGGER,
            name="Suncloud Data",
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
            _LOGGER.error("Failed to fetch plant data")
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

async def get_open_points(config, device_type=11, device_model_id=None):
    """Retrieve list of open telemetry points for a device type."""
    payload = {
        "device_type": str(device_type),
        "type": 2,  # 2 = remote telemetry points
        "curPage": 1,
        "size": 999
    }

    if device_model_id:
        payload["device_model_id"] = str(device_model_id)

    result = await post_request(None, config, "/openapi/getOpenPointInfo", payload)
    if not result or result.get("result_code") != "1":
        _LOGGER.error("Failed to fetch open point info")
        return []

    points = result.get("result_data", {}).get("pageList", [])
    return [
        {
            "id": str(p.get("point_id")),
            "name": p.get("point_name"),
            "unit": p.get("show_unit")
        }
        for p in points
    ]
