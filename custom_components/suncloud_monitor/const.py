"""Constants for the Suncloud Monitor integration."""

DOMAIN = "suncloud_monitor"

# Default API Base URL
API_BASE_URL = "https://gateway.isolarcloud.eu"

# API Endpoints
LOGIN_ENDPOINT = "/openapi/login"
PLANT_LIST_ENDPOINT = "/openapi/getPowerStationList"
DEVICE_LIST_ENDPOINT = "/openapi/getDeviceList"
PLANT_INFO_ENDPOINT = "/openapi/getPowerStationDetail"
REALTIME_ENDPOINT = "/openapi/getDeviceRealTimeData"
POINT_DISCOVERY_ENDPOINT = "/openapi/getOpenPointInfo"

# HA state keys
TOKEN_KEY = "input_text.token"
PS_KEY_STATE = "input_text.ps_key"
PLANT_ID_STATE = "sensor.plant_id"
METER_SN_STATE = "sensor.meter_sn"

# UI helpers
TELEMETRY_SELECT = "input_select.telemetry_points"
