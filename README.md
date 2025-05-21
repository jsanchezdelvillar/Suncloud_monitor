# 🌞 Suncloud Monitor – Home Assistant Integration

![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)
![license](https://img.shields.io/github/license/jsanchezdelvillar/Suncloud_monitor)
![version](https://img.shields.io/github/v/tag/jsanchezdelvillar/Suncloud_monitor)

A Home Assistant integration to monitor **Sungrow Suncloud** plants using secure **RSA & AES**-encrypted API calls.

---

## 🔐 Features

- Secure login using public RSA key
- Real-time telemetry data from your plant (power, yield, energy)
- Configurable via Home Assistant UI
- Supports `input_select` to enable/disable telemetry points
- Full HACS support
- Built-in automation polling + statistics

---

## 🧩 Installation

1. Copy this repo to:  
   `/config/custom_components/suncloud_monitor/`
2. Restart Home Assistant
3. Add via **Settings → Devices & Services → + Add Integration**
4. Enter your:
   - Sungrow account credentials
   - AppKey, access key, RSA public key (base64 DER)
   - Your `ps_key` (plant ID)

---

## 📡 Available Sensors

| Sensor | Icon | Device Class | Unit |
|--------|------|--------------|------|
| Daily Yield | 🔋 `mdi:transmission-tower` | `energy` | `Wh` |
| Current Power | ⚡ `mdi:flash` | `power` | `W` |
| Energy Fed In / Purchased | ↔️ | `energy` | `Wh` |
| Load Power | ⚡ | `power` | `W` |
| Self Sufficiency % | 📊 | - | `%` |

---

## 📦 Configuration (optional)

### `secrets.yaml`
```yaml
suncloud_username: your@email.com
suncloud_password: yourpassword
suncloud_appkey: your_app_key
suncloud_secret: your_secret_key
suncloud_rsa_key: base64_RSA_key
