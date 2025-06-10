"""Sensor platform for Suncloud Monitor."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, CONF_POINTS
from .coordinator import SuncloudDataCoordinator


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensors from config entry."""
    coordinator: SuncloudDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    selected_points = config_entry.options.get(CONF_POINTS)
    if selected_points:
        points = {
            pid: config
            for pid, config in coordinator.points.items()
            if pid in selected_points
        }
    else:
        points = coordinator.points

    sensors = [
        SuncloudSensor(
            coordinator,
            point_id,
            config.get("point_name"),
            config.get("unit"),
        )
        for point_id, config in points.items()
    ]

    async_add_entities(sensors)


class SuncloudSensor(SensorEntity):
    def __init__(
        self,
        coordinator: SuncloudDataCoordinator,
        point_id: str,
        name: str = None,
        unit: str = None,
    ) -> None:
        self.coordinator = coordinator
        self._point_id = str(point_id)
        self._name = name
        self._unit = unit

    @property
    def name(self) -> str:
        if self._name:
            return f"{self._point_id} - {self._name}"
        config = self.coordinator.get_point_config(self._point_id)
        name = config.get("point_name") if config else None
        return f"{self._point_id} - {name}" if name else self._point_id

    @property
    def unique_id(self) -> str:
        return f"suncloud_sensor_{self._point_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._point_id)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._unit:
            return self._unit
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
