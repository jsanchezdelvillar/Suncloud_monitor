from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import ENERGY_KILO_WATT_HOUR, POWER_WATT

from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up SunCloud sensors from config entry."""

    point_ids = hass.states.get("input_select.telemetry_points").attributes.get("options", [])

    sensors = []
    for point_id in point_ids:
        sensors.append(SunCloudSensor(point_id))

    async_add_entities(sensors, update_before_add=True)


class SunCloudSensor(Entity):
    """Representation of a SunCloud sensor."""

    def __init__(self, point_id):
        self._attr_name = f"Plant Point {point_id}"
        self._attr_unique_id = f"suncloud_point_{point_id}"
        self._point_id = point_id

    @property
    def state(self):
        return self.hass.states.get(f"sensor.plant_point_{self._point_id}").state

    @property
    def unit_of_measurement(self):
        point = self.hass.states.get(f"sensor.plant_point_{self._point_id}")
        if point and "unit" in point.attributes:
            return point.attributes["unit"]
        return None

    @property
    def should_poll(self):
        return False

    async def async_update(self):
        """No-op: data pushed by API."""
        pass
