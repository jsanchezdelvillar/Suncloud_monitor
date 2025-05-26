import json
import requests

@service
def suncloud_get_plant_info():
    """
    Uses meter SN to fetch ps_key and store in input_text.ps_key
    """

    token = state.get("input_text.token")
    meter_sn = state.get("sensor.meter_sn")

    if not token or token == "Error":
        log.error("[PLANT INFO] Token is invalid. Run suncloud_login_api first.")
        return

    if not meter_sn or meter_sn == "none":
        log.error("[PLANT INFO] No meter SN. Run suncloud_get_device_list first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getPowerStationDetail"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    payload = {
        "sn": meter_sn,
        "is_get_ps_remarks": "1"
    }

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()

            if result.get("result_code") == "1":
                data = result.get("result_data", {})
                ps_key = data.get("ps_key", "")
                ps_name = data.get("ps_name", "Unknown")

                if ps_key:
                    state.set("input_text.ps_key", ps_key)
                    log.info(f"[PLANT INFO] Retrieved ps_key for '{ps_name}': {ps_key}")
                else:
                    log.warning("[PLANT INFO] No ps_key returned from API.")

            else:
                log.error(f"[PLANT INFO] API Error: {result.get('result_msg')}")

        else:
            log.error(f"[PLANT INFO] HTTP {response.status_code}: {response.text}")

    except Exception as e:
        log.error(f"[PLANT INFO] Exception: {e}")
