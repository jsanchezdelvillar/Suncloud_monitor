import json
import requests

@service
def get_plant_list(curPage: int = 1, size: int = 10):
    """
    Fetch plant list from Sungrow and store first ps_id as sensor.plant_id
    """

    token = state.get("input_text.token")
    if not token or token == "Error":
        log.error("[PLANT LIST] Token not available. Run login_api first.")
        return

    url = "https://gateway.isolarcloud.eu/openapi/getPowerStationList"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    payload = {
        "curPage": curPage,
        "size": size
    }

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()

            if result.get("result_code") == "1":
                plants = result.get("result_data", {}).get("pageList", [])
                if plants:
                    first_plant = plants[0]
                    ps_id = first_plant.get("ps_id")
                    ps_name = first_plant.get("ps_name")

                    state.set("sensor.plant_id", ps_id)
                    log.info(f"[PLANT LIST] Set ps_id: {ps_id} for plant: {ps_name}")
                else:
                    log.warning("[PLANT LIST] No plants found.")
            else:
                log.error(f"[PLANT LIST] API Error: {result.get('result_msg')}")

        else:
            log.error(f"[PLANT LIST] HTTP {response.status_code}: {response.text}")

    except Exception as e:
        log.error(f"[PLANT LIST] Exception: {e}")
