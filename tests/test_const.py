from custom_components.suncloud_monitor import const


def test_constants_present():
    assert hasattr(const, "DOMAIN")
    assert hasattr(const, "PLATFORMS")
