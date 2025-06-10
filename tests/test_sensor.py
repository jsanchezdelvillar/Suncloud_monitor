from custom_components.suncloud_monitor.sensor import SuncloudSensor


class DummyCoordinator:
    def __init__(self, data=None, ps_id=None):
        self.data = data
        self.ps_id = ps_id


def test_sensor_entity_creation():
    coordinator = DummyCoordinator()
    sensor = SuncloudSensor(
        coordinator=coordinator, point_id="123", name="Test Point", unit="Wh"
    )
    assert sensor._attr_unique_id == "suncloud_123"
    assert sensor._attr_name == "Test Point"
    assert sensor._attr_native_unit_of_measurement == "Wh"
    assert sensor._point_id == "123"


def test_native_value_returns_data():
    coordinator = DummyCoordinator(data={"123": 42})
    sensor = SuncloudSensor(
        coordinator=coordinator, point_id="123", name="Test Point", unit="Wh"
    )
    assert sensor.native_value == 42


def test_native_value_returns_none_if_no_data():
    coordinator = DummyCoordinator(data=None)
    sensor = SuncloudSensor(
        coordinator=coordinator, point_id="999", name="Test Point", unit="Wh"
    )
    assert sensor.native_value is None


def test_device_info_with_ps_id():
    coordinator = DummyCoordinator(ps_id="plant123")
    sensor = SuncloudSensor(
        coordinator=coordinator, point_id="123", name="Test Point", unit="Wh"
    )
    info = sensor.device_info
    assert info["identifiers"] == {("suncloud_monitor", "plant123")}
    assert info["name"] == "Sungrow plant123"


def test_device_info_without_ps_id():
    coordinator = DummyCoordinator(ps_id=None)
    sensor = SuncloudSensor(
        coordinator=coordinator, point_id="123", name="Test Point", unit="Wh"
    )
    info = sensor.device_info
    assert info["identifiers"] == {("suncloud_monitor", "unknown_plant")}
    assert info["name"] == "Sungrow unknown_plant"
