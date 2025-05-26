import json
import requests

@service
def suncloud_get_device_list():
    """
    Fetch device list for current plant and store meter SN (type 7) to sensor.meter_sn
    """

    token = state.get("input_text.token")
    ps_id = state.get("sensor.plant_id")

    if not token or token == "Error":
        log.error("[DEVICE LIST] Missing or invalid token. Run suncloud_login_api first.")
        return

    if not ps_id or ps_id == "none":
        log.error("[DEVICE LIST] No plant ID found. Run suncloud_get_plant_list first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getDeviceList"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    payload = {
        "curPage": 1,
        "size": 50,
        "ps_id": ps_id
    }

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()

            if result.get("result_code") == "1":
                devices = result.get("result_data", {}).get("pageList", [])
                for dev in devices:
                    if dev.get("device_type") == 7:
                        dev_sn = dev.get("device_sn")
                        dev_name = dev.get("device_name")
                        log.info(f"[DEVICE LIST] Found meter '{dev_name}' SN: {dev_sn}")
                        state.set("sensor.meter_sn", dev_sn)
                        return
                log.warning("[DEVICE LIST] No device of type 7 (meter) found")
            else:
                log.error(f"[DEVICE LIST] API Error: {result.get('result_msg')}")
        else:
            log.error(f"[DEVICE LIST] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.error(f"[DEVICE LIST] Exception: {e}")
