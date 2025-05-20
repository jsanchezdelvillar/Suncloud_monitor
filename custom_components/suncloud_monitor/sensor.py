import json
from homeassistant.helpers.entity import Entity

class SunCloudSensor(Entity):
    def __init__(self, point_id):
        self._point_id = point_id
        self._attr_unique_id = f"suncloud_point_{point_id}"
        self._attr_name = f"Plant Point {point_id}"

        meta_json = self.hass.states.get("sensor.point_meta_json")
        meta = {}

        if meta_json and meta_json.state:
            try:
                meta_dict = json.loads(meta_json.state)
                meta = meta_dict.get(point_id, {})
            except Exception as e:
                self._attr_icon = "mdi:gauge"
                log.warning(f"Failed to parse point metadata: {e}")

        self._attr_icon = meta.get("icon", "mdi:gauge")
        self._attr_unit_of_measurement = meta.get("unit", None)
        self._device_class = meta.get("device_class", None)

    @property
    def state(self):
        return self.hass.states.get(f"sensor.plant_point_{self._point_id}").state

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def device_class(self):
        return self._device_class

    @property
    def icon(self):
        return self._attr_icon

    @property
    def state_class(self):
        return "measurement"

    @property
    def should_poll(self):
        return False
