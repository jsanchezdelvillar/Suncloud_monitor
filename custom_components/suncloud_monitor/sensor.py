"""Sensor platform for Suncloud Monitor."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import SuncloudDataCoordinator


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensors from config entry."""
    coordinator: SuncloudDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []
    for point_id in coordinator.points:
        sensors.append(SuncloudSensor(coordinator, point_id))

    async_add_entities(sensors)


class SuncloudSensor(SensorEntity):
    def __init__(self, coordinator: SuncloudDataCoordinator, point_id: str) -> None:
        self.coordinator = coordinator
        self._point_id = str(point_id)

    @property
    def name(self) -> str:
        config = self.coordinator.get_point_config(self._point_id)
        name = config.get("name") if config else None
        return f"{self._point_id} - {name}" if name else self._point_id

    @property
    def unique_id(self) -> str:
        return f"suncloud_sensor_{self._point_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._point_id)

    @property
    def native_unit_of_measurement(self) -> str | None:
        config = self.coordinator.get_point_config(self._point_id)
        return config.get("unit") if config else None

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def entity_category(self) -> EntityCategory | None:
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "suncloud_device")},
            "name": "Suncloud Monitor",
            "manufacturer": "Suncloud",
        }
