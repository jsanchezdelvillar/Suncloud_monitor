import aiohttp
import json
import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)


async def post_request(hass, config: dict, endpoint: str, payload: dict, token: Optional[str] = None):
    """Send a POST request to the Suncloud API."""
    base_url = config.get("base_url", "https://gateway.isolarcloud.eu")
    url = f"{base_url}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Home Assistant",
        "appkey": config.get("appkey"),
        "sys_code": "901",
    }

    if token:
        headers["token"] = token
    if "sung_secret" in config:
        headers["x-access-key"] = config.get("sung_secret")
    if "x-random-secret-key" in config:
        headers["x-random-secret-key"] = config.get("x-random-secret-key")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    _LOGGER.warning(f"Suncloud API call failed: {resp.status}")
                    return None
                return await resp.json()
    except Exception as e:
        _LOGGER.error(f"Suncloud API request error: {e}")
        return None
