import json
import requests

@service
def get_suncloud_points():
    """
    Fetch available telemetry points for device_type 11 and push to input_select.telemetry_points.
    """

    token = state.get("input_text.token")
    model_id = "367701"  # default model ID
    base_url = "https://gateway.isolarcloud.eu"
    endpoint = "/openapi/getOpenPointInfo"

    if not token or token == "Error":
        log.error("[POINTS] Token not available. Run login first.")
        return

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    payload = {
        "device_type": 11,
        "type": 2,
        "curPage": 1,
        "size": 999,
        "device_model_id": model_id
    }

    try:
        response = task.executor(requests.post, f"{base_url}{endpoint}", headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()
            points = result.get("result_data", {}).get("pageList", [])

            valid_ids = [str(p.get("point_id")) for p in points if "point_id" in p]

            if valid_ids:
                state.set("input_select.telemetry_points", {"options": valid_ids})
                log.info(f"[POINTS] Set {len(valid_ids)} telemetry points to input_select.telemetry_points")
            else:
                log.warning("[POINTS] No valid telemetry point_ids found")

        else:
            log.error(f"[POINTS] HTTP Error {response.status_code}: {response.text}")

    except Exception as e:
        log.error(f"[POINTS] Exception: {e}")
