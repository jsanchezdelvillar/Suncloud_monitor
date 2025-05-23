"""Pyscript service to fetch Suncloud telemetry points and update input_select."""

import json
from custom_components.suncloud_monitor.api import get_open_points

# The decorator and objects below are provided by the Pyscript runtime.
# pylint: disable=undefined-variable

@service  # type: ignore[name-defined]
async def get_suncloud_points():
    """Fetch available telemetry points and update input_select."""
    config = {
        "RSA_public": secrets["suncloud_rsa_key"],  # type: ignore[name-defined]
        "sung_secret": secrets["suncloud_secret"],  # type: ignore[name-defined]
        "base_url": "https://gateway.isolarcloud.eu",
        "appkey": secrets["suncloud_appkey"]        # type: ignore[name-defined]
    }

    points = await get_open_points(config, device_type=11)
    if not points:
        log.error("No points returned from Sungrow API.")  # type: ignore[name-defined]
        return

    # Print list to log
    for pt in points:
        log.info(f"[{pt['id']}] {pt['name']} ({pt['unit']})")  # type: ignore[name-defined]

    # Extract just the IDs to set in input_select
    point_ids = [pt["id"] for pt in points]
    input_select.set_options("telemetry_points", point_ids)  # type: ignore[name-defined]
    log.info(f"Updated input_select.telemetry_points with {len(point_ids)} points.")  # type: ignore[name-defined]
