from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for point_id, meta in coordinator.points.items():
        sensor = SuncloudSensor(
            coordinator=coordinator,
            point_id=point_id,
            name=meta.get("name", f"Point {point_id}"),
            unit=meta.get("unit", ""),
        )
        entities.append(sensor)
    async_add_entities(entities, True)


class SuncloudSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, point_id, name, unit):
        super().__init__(coordinator)
        self._attr_unique_id = f"suncloud_{point_id}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = None
        self._attr_state_class = "measurement"
        self._point_id = point_id

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get(self._point_id)

    @property
    def device_info(self):
        ps_id = getattr(self.coordinator, "ps_id", None)
        if not ps_id:
            ps_id = "unknown_plant"
        return {
            "identifiers": {(DOMAIN, str(ps_id))},
            "name": f"SunCloud Plant {ps_id}",
            "manufacturer": "Sungrow",
            "model": "SunCloud Monitor",
            "sw_version": "1.0.0",
        }
