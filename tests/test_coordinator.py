import pytest
from custom_components.suncloud_monitor.coordinator import SuncloudDataCoordinator

@pytest.mark.asyncio
async def test_rsa_encrypt():
    coordinator = SuncloudDataCoordinator(None, {})
    # Should return base64 string or empty string
    result = coordinator._rsa_encrypt("test", "invalidkey===")
    assert isinstance(result, str)
