import json
import requests
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from .const import DOMAIN

async def async_setup_api(hass, config):
    """Set up the SunCloud Monitor API polling."""

    token = None
    ps_key = None

    async def login_api():
        nonlocal token
        username = config.get("username")
        password = config.get("password")
        base_url = config.get("base_url")

        url = f"{base_url}/openapi/login"
        headers = {"Content-Type": "application/json"}
        payload = {
            "user_account": username,
            "user_password": password
        }

        try:
            response = await hass.async_add_executor_job(lambda: requests.post(url, headers=headers, json=payload))
            result = response.json()
            token = result.get("result_data", {}).get("token")
            hass.states.async_set("sensor.api_login_token", token or "none")
        except Exception as e:
            hass.states.async_set("sensor.api_login_token", "none")
            raise e

    async def get_plant_list():
        nonlocal token
        base_url = config.get("base_url")
        url = f"{base_url}/openapi/getPowerStationList"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        payload = {"curPage": 1, "size": 10}

        response = await hass.async_add_executor_job(lambda: requests.post(url, headers=headers, json=payload))
        result = response.json()
        ps_list = result.get("result_data", {}).get("pageList", [])
        if ps_list:
            hass.states.async_set("sensor.plant_id", ps_list[0].get("ps_id"))

    async def get_device_list():
        nonlocal token
        base_url = config.get("base_url")
        ps_id = hass.states.get("sensor.plant_id").state
        url = f"{base_url}/openapi/getDeviceList"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        payload = {"curPage": 1, "size": 10, "ps_id": int(ps_id)}

        response = await hass.async_add_executor_job(lambda: requests.post(url, headers=headers, json=payload))
        result = response.json()
        devices = result.get("result_data", {}).get("pageList", [])
        for dev in devices:
            if dev.get("device_type") == 7:
                meter_sn = dev.get("device_sn")
                hass.states.async_set("sensor.meter_sn", meter_sn)
                break

    async def get_plant_info():
        nonlocal token, ps_key
        base_url = config.get("base_url")
        meter_sn = hass.states.get("sensor.meter_sn").state
        url = f"{base_url}/openapi/getPowerStationDetail"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        payload = {"sn": meter_sn, "is_get_ps_remarks": "1"}

        response = await hass.async_add_executor_job(lambda: requests.post(url, headers=headers, json=payload))
        result = response.json()
        data = result.get("result_data", {})
        ps_key = data.get("ps_key")
        hass.states.async_set("sensor.ps_key", ps_key)

    async def get_plant_values():
        nonlocal token, ps_key
        base_url = config.get("base_url")
        url = f"{base_url}/openapi/getDeviceRealTimeData"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        ps_key = hass.states.get("sensor.ps_key").state

        point_ids = hass.states.get("input_select.telemetry_points").attributes.get("options")
        payload = {
            "point_id_list": point_ids,
            "ps_key_list": [ps_key],
            "device_type": 11
        }

        response = await hass.async_add_executor_job(lambda: requests.post(url, headers=headers, json=payload))
        result = response.json()
        data = result.get("result_data", [])
        for point in data:
            pid = point.get("point_id")
            val = point.get("value")
            unit = point.get("unit")
            hass.states.async_set(f"sensor.plant_point_{pid}", val)

    async def get_plant_values_resilient(_now=None):
        """Scheduled job that retries missing data."""
        try:
            token_state = hass.states.get("sensor.api_login_token")
            ps_key_state = hass.states.get("sensor.ps_key")

            if not token_state or token_state.state == "none":
                await login_api()
            if not ps_key_state or ps_key_state.state == "none":
                await get_plant_list()
                await get_device_list()
                await get_plant_info()

            await get_plant_values()

        except Exception as e:
            hass.states.async_set("sensor.plant_polling_error", str(e))

    # Run poller every X minutes
    poll_minutes = config.get("poll_interval", 5)
    async_track_time_interval(hass, get_plant_values_resilient, timedelta(minutes=poll_minutes))

    return True
