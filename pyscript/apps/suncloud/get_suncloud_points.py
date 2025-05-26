import json
import requests

@service
def suncloud_get_suncloud_points():
    """
    Fetch available telemetry points and populate input_select.telemetry_points
    """

    token = state.get("input_text.token")
    if not token or token == "Error":
        log.error("[POINTS] Token is missing or invalid. Run suncloud_login_api first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getOpenPointInfo"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    payload = {
        "device_type": 11,
        "type": 2,
        "curPage": 1,
        "size": 999,
        "device_model_id": "367701"
    }

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()

            if result.get("result_code") == "1":
                points = result.get("result_data", {}).get("pageList", [])
                ids = [str(p["point_id"]) for p in points if "point_id" in p]
                state.set("input_select.telemetry_points", {"options": ids})
                log.info(f"[POINTS] Loaded {len(ids)} telemetry points into input_select")
            else:
                log.error(f"[POINTS] API Error: {result.get('result_msg')}")
        else:
            log.error(f"[POINTS] HTTP Error {response.status_code}: {response.text}")
    except Exception as e:
        log.error(f"[POINTS] Exception: {e}")
