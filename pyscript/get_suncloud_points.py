import json
from custom_components.suncloud_monitor.api import get_open_points

@service
async def get_suncloud_points():
    """Fetch available telemetry points and update input_select."""
    config = {
        "RSA_public": secrets["suncloud_rsa_key"],
        "sung_secret": secrets["suncloud_secret"],
        "base_url": "https://gateway.isolarcloud.eu",
        "appkey": secrets["suncloud_appkey"]
    }

    points = await get_open_points(config, device_type=11)
    if not points:
        log.error("No points returned from Sungrow API.")
        return

    # Print list to log
    for pt in points:
        log.info(f"[{pt['id']}] {pt['name']} ({pt['unit']})")

    # Extract just the IDs to set in input_select
    point_ids = [pt["id"] for pt in points]
    input_select.set_options("telemetry_points", point_ids)
    log.info(f"Updated input_select.telemetry_points with {len(point_ids)} points.")
