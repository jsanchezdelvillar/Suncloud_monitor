"""API helpers for the Suncloud Monitor integration."""

import logging
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)

SENSOR_DEFINITIONS = {
    "83022": {
        "name": "Daily Yield",
        "unit": "Wh",
        "device_class": "energy",
        "icon": "mdi:transmission-tower",
        "state_class": "total_increasing",
    },
    "83033": {
        "name": "Current Power",
        "unit": "W",
        "device_class": "power",
        "icon": "mdi:flash",
        "state_class": "measurement",
    },
    "83025": {
        "name": "Equivalent Hours",
        "unit": "h",
        "icon": "mdi:clock",
        "state_class": "measurement",
    },
    "83102": {
        "name": "Energy Purchased",
        "unit": "Wh",
        "device_class": "energy",
        "icon": "mdi:transmission-tower",
        "state_class": "total_increasing",
    },
    "83072": {
        "name": "Energy Fed In",
        "unit": "Wh",
        "device_class": "energy",
        "icon": "mdi:transmission-tower-export",
        "state_class": "total_increasing",
    },
    "83106": {
        "name": "Load Power",
        "unit": "W",
        "device_class": "power",
        "icon": "mdi:lightning-bolt",
        "state_class": "measurement",
    },
}

def unused_function(_config, _discovery_info=None):
    """An example function with unused arguments."""
    # pylint: disable=unused-argument

class ExampleCoordinator:
    """Example coordinator class."""

    def __init__(self):
        """Initialize the example coordinator."""

    async def fetch_data(self):
        """Simulate fetching data."""

class AnotherExample:
    """Another example class."""

    def __init__(self):
        """Initialize another example."""

    def do_something(self):
        """Do something."""

async def long_line_function(
    _config,
    _discovery_info=None
):
    """Function with previously long line, now broken up."""
    # pylint: disable=unused-argument
