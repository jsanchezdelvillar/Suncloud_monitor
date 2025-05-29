from custom_components.suncloud_monitor.sensor import SuncloudSensor

def test_sensor_entity_creation():
    meta = {"name": "Test Point", "unit": "Wh"}
    sensor = SuncloudSensor(coordinator=None, pid="123", meta=meta)
    assert sensor._attr_unique_id == "suncloud_123"
    assert sensor._attr_name == "SunCloud 123_Test Point"
