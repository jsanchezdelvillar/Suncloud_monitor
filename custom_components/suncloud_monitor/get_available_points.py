import json
import logging
import requests

_LOGGER = logging.getLogger(__name__)

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

def get_available_points(token, api_url, hass=None, telemetry_entity_id="input_select.telemetry_points"):
    """
    Queries open telemetry points and stores metadata for each point.
    Args:
        token (str): API Authorization token.
        api_url (str): Base API URL.
        hass (HomeAssistant, optional): Home Assistant instance for state/service integration.
        telemetry_entity_id (str): Home Assistant entity ID to update.
    Returns:
        dict: point_meta, or None if failed.
    """
    if not token or token == "none":
        _LOGGER.error("[POINT INFO] No login token. Run login_api first.")
        return None

    url = f"{api_url}/openapi/getOpenPointInfo"
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
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result.get("result_code") == "1":
            points = result.get("result_data", {}).get("pageList", [])
            _LOGGER.info("[POINT INFO] Found %d telemetry points.", len(points))

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

            # If Home Assistant instance is provided, update states/services
            if hass is not None:
                hass.states.async_set("sensor.point_meta_json", json.dumps(point_meta))
                point_ids = list(point_meta.keys())
                hass.async_create_task(
                    hass.services.async_call(
                        "input_select", "set_options",
                        {
                            "entity_id": telemetry_entity_id,
                            "options": point_ids
                        }
                    )
                )
            return point_meta
        else:
            _LOGGER.error("[POINT INFO] API error: %s", result.get('result_msg'))
    except requests.RequestException as e:
        _LOGGER.error("[POINT INFO] HTTP request failed: %s", e)
    except Exception as e:
        _LOGGER.exception("[POINT INFO] Unexpected exception: %s", e)
    return None
