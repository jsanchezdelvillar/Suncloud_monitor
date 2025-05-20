import json
import requests

@service
def get_available_points():
    """
    Queries open telemetry points and stores metadata for each point.
    """
    token = state.get("sensor.api_login_token")

    if not token or token == "none":
        log.error("[POINT INFO] No login token. Run login_api first.")
        return

    url = "https://your-api-url.com/openapi/getOpenPointInfo"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    payload = {
        "device_type": 11,
        "type": 2,
        "curPage": 1,
        "size": 999
    }

    try:
        response = task.executor(requests.post, url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()
            if result.get("result_code") == "1":
                points = result.get("result_data", {}).get("pageList", [])
                log.info(f"[POINT INFO] Found {len(points)} telemetry points.")

                point_meta = {}
                for pt in points:
                    pid = str(pt.get("point_id"))
                    unit = pt.get("show_unit", "")
                    name = pt.get("point_name", "")
                    device_class, icon = classify_point(unit, name)

                    point_meta[pid] = {
                        "unit": unit,
                        "name": name,
                        "device_class": device_class,
                        "icon": icon
                    }

                # Store the full map as a JSON string
                state.set("sensor.point_meta_json", json.dumps(point_meta))

                # Also update input_select with all point IDs
                point_ids = list(point_meta.keys())
                service.call("input_select.set_options", {
                    "entity_id": "input_select.telemetry_points",
                    "options": point_ids
                })

            else:
                log.error(f"[POINT INFO] API error: {result.get('result_msg')}")

        else:
            log.error(f"[POINT INFO] HTTP {response.status_code}: {response.text}")

    except Exception as e:
        log.error(f"[POINT INFO] Exception: {e}")

def classify_point(unit: str, name: str):
    """Infer device_class and icon from unit or name."""
    unit = unit.lower()

    if unit in ["kwh", "wh"]:
        return "energy", "mdi:lightning-bolt"
    if unit in ["w"]:
        return "power", "mdi:flash"
    if unit in ["v"]:
        return "voltage", "mdi:alpha-v"
    if unit in ["a"]:
        return "current", "mdi:current-ac"
    if "co2" in name.lower():
        return "carbon_dioxide", "mdi:co2"
    if "temp" in name.lower():
        return "temperature", "mdi:thermometer"
    if "hour" in name.lower():
        return "duration", "mdi:clock-outline"
    if "income" in name.lower():
        return None, "mdi:currency-cny"

    return None, "mdi:gauge"
