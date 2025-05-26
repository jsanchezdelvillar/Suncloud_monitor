# <img src="https://raw.githubusercontent.com/jsanchezdelvillar/Suncloud_monitor/main/custom_components/suncloud_monitor/icon.png" width="48" height="48"> Suncloud Monitor – Home Assistant Integration

![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)
![license](https://img.shields.io/github/license/jsanchezdelvillar/Suncloud_monitor)
![version](https://img.shields.io/github/v/tag/jsanchezdelvillar/Suncloud_monitor)

A Home Assistant integration to monitor your **Sungrow Suncloud** solar plant using secure RSA/AES-encrypted API requests.

---

## Features

- RSA/AES encrypted communication (required by Sungrow)
- Real-time telemetry for:
    - Power, Yield, Feed-In, Grid Import, Self-Consumption %
- Auto-discovery of available telemetry points
- Pyscript integration for advanced control
- Lovelace dashboard card to choose & refresh telemetry
- Fully HACS-compatible

---

## Installation

### HACS (Recommended)

1. Go to HACS → Integrations → 3 dots → Custom Repositories
2. Add this URL:  
   `https://github.com/jsanchezdelvillar/Suncloud_monitor`  
   Category: Integration
3. Install `Suncloud Monitor` from HACS
4. Restart Home Assistant
5. Go to Settings → Devices & Services → + Add Integration
6. Search: **Suncloud Monitor**

---

### Manual Installation

1. Download this repository as ZIP
2. Extract to:  
   `/config/custom_components/suncloud_monitor/`
3. Restart Home Assistant

---

## Required Manual Configuration

These files must be manually added or modified:

### configuration.yaml

    pyscript:
      allow_all_imports: true
      apps: true

    input_select: !include input_select.yaml
    automation: !include automations.yaml

---

### input_select.yaml

    telemetry_points:
      name: Telemetry Points
      options:
        - 83022
        - 83033
        - 83025
        - 83102
        - 83072
        - 83106
      initial: 83022
      icon: mdi:chart-line

---

### automations.yaml

    - alias: "Suncloud Monitor – Update Data"
      id: suncloud_monitor_update
      trigger:
        - platform: time_pattern
          minutes: "/5"
      action:
        - service: pyscript.update_device_data_RSA

---

### secrets.yaml

    suncloud_username: your@email.com
    suncloud_password: yourpassword
    suncloud_appkey: your_app_key
    suncloud_secret: your_access_key
    suncloud_rsa_key: Base64_RSA_public_key

---

## Pyscript Service

**Service:** `pyscript.get_suncloud_points`  
Fetches all available telemetry points from the Sungrow API and updates `input_select.telemetry_points`.

To call:  
Go to **Developer Tools → Services → Call Service → pyscript.get_suncloud_points**

---

## Lovelace Card Setup

You can add a manual control card to your dashboard for telemetry selection and refresh.

### Steps (UI Mode):

Go to **Overview → Edit Dashboard**
Click **+ Add Card → Manual**
Paste this:

    type: vertical-stack  
    cards:
      - type: entities
        title: Suncloud Monitor
        entities:
          - entity: input_select.telemetry_points
          - type: button
            name: Refresh Telemetry Points
            icon: mdi:refresh
            tap_action:
              action: call-service
              service: pyscript.get_suncloud_points

✅ This gives you a dropdown of telemetry point IDs and a refresh button.

---

## Testing

- Call `pyscript.get_suncloud_points`
- Confirm that `input_select.telemetry_points` is updated
- View available telemetry point names in the log output

---

## License

MIT License  
© [jsanchezdelvillar](https://github.com/jsanchezdelvillar)

---

## Contributing

Pull requests are welcome.  
Open an issue at:  
[https://github.com/jsanchezdelvillar/Suncloud_monitor](https://github.com/jsanchezdelvillar/Suncloud_monitor)

