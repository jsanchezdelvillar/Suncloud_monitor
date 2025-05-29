# 🌞 SunCloud Monitor – Home Assistant Integration

![Version](https://img.shields.io/github/v/tag/jsanchezdelvillar/Suncloud_monitor?label=version)
![License](https://img.shields.io/github/license/jsanchezdelvillar/Suncloud_monitor)
![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue.svg?logo=home-assistant)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.0+-blue?logo=home-assistant)
![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python)
![Last Commit](https://img.shields.io/github/last-commit/jsanchezdelvillar/Suncloud_monitor)
![Issues](https://img.shields.io/github/issues/jsanchezdelvillar/Suncloud_monitor)
![Code size](https://img.shields.io/github/languages/code-size/jsanchezdelvillar/Suncloud_monitor)
![Build](https://github.com/jsanchezdelvillar/Suncloud_monitor/actions/workflows/ci.yml/badge.svg)
![Stars](https://img.shields.io/github/stars/jsanchezdelvillar/Suncloud_monitor.svg?style=social)
![Forks](https://img.shields.io/github/forks/jsanchezdelvillar/Suncloud_monitor.svg?style=social)

> Full-featured, encrypted Home Assistant integration for monitoring your SunCloud plant, inverter, and telemetry points.

---

## ✋ Requirements!

- You must have an account in iSolarCloud
- From iSolarCloud access `Developer portal`, `Applications` and then `Create application`
- Fill the data. Under `Authorize with OAuth2.0 (Mandatory for Version V2)` select `No`
- Sungrow will give you your Appkey, Secret Key and RSA Public Key in a couple of days

---

## 🚀 Features

✅ Encrypted RSA/AES login to isolarcloud  
✅ Auto-recovering `token`, `ps_key`, `sn`, and telemetry points  
✅ Fully UI-configurable via Home Assistant  
✅ Dynamic sensors for 70+ telemetry points  
✅ HACS compatible  
✅ Optional: Debug mode via Pyscript for power users

---

## 📦 Installation

### ✅ Recommended: via HACS

1. Add repository to HACS:
   - URL: `https://github.com/YOUR_USERNAME/Suncloud_monitor`
   - Category: Integration
2. Install and restart Home Assistant.
3. Go to **Settings > Devices & Services > Add Integration**
4. Search for `SunCloud Monitor` and follow the setup flow.

---

## ⚙️ Configuration

No need to edit `configuration.yaml`. All setup is done via the UI.

You'll be prompted to enter:

- Username
- Password
- AppKey
- Access Key
- RSA Public Key (Base64-encoded)

You can choose which telemetry points to expose as sensors.

---

## 🧠 Manual Debug Mode (Pyscript)

For advanced users or debugging, you can use the original working Pyscript logic.

### Setup

1. Install [Pyscript](https://github.com/custom-components/pyscript) via HACS
2. In `configuration.yaml`, add:

   ```yaml
   pyscript: !include pyscript/config.yaml
   ```

3. Place the original `Suncloud_monitor/pyscript/apps/suncloud/__init__.py` in `/config/pyscript/apps/suncloud/` directory.
4. Place the original `Suncloud_monitor/pyscript/config.py` in `/config/pyscript/` directory or, if it exists, add its contents to the file.

### Add this to your secrets.yaml

```yaml
suncloud_username: your@email.com
suncloud_password: your_password
suncloud_appkey: your_appkey
suncloud_access_key: your_accesskey
suncloud_rsa_key: your_base64_rsa_public_key
```

### Required Helper

Add to `configuration.yaml`:

```yaml
input_text:
  token:
    name: SunCloud Token
    initial: ""
```

### Manual Services (via Developer Tools > Services)

- `pyscript.suncloud_login_api` Using the data from `secrets.yaml` it obtains the token and stores it in `input_text.token`
- `pyscript.suncloud_get_plant_list` Obtains `ps_id` and stores it in `config_storage'.yaml`
- `pyscript.suncloud_get_device_list` Obtains `sn` and stores it in `config_storage'.yaml`
- `pyscript.suncloud_get_plant_info` Obtains `ps_key` and stores it in `config_storage'.yaml`
- `pyscript.suncloud_get_suncloud_points` Obtains all available points and stores them in `config_storage'.yaml`
- `pyscript.suncloud_get_realtime_data` Updates the values of the points. Create an automation if you want to update the points periodically

---

## 📁 File Structure

```text
Suncloud_monitor/
├── custom_components/
│   └── suncloud_monitor/
│       ├── __init__.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       ├── const.py
│       ├── manifest.json
│       ├── services.yaml
│       ├── hacs.json
│       ├── strings.json
│       ├── config_storage.yaml
│       └── translations/
│           ├── en.json
│           └── es.json
├── pyscript/
│   ├── config.yaml
│   └── apps/
│       └── suncloud/
│           └── __init__.py    # Original working Pyscript
├── README.md
└── LICENSE
```

---

## 🧪 Telemetry Point Examples

| Sensor ID                  | Description                     | Unit |
|----------------------------|----------------------------------|------|
| `sensor.suncloud_83001`    | Inverter AC power normalization | W/Wp |
| `sensor.suncloud_83006`    | Meter daily yield               | Wh   |
| `sensor.suncloud_83326`    | Energy storage active power     | W    |

> 🧠 All point mappings live in `config_storage.yaml`

---

## 👤 Maintainer

- GitHub: [@jsanchezdelvillar](https://github.com/jsanchezdelvillar)
- Built with ❤️ and encrypted brainwaves 🧠🔐

---

## 🛡️ License

MIT License. See `LICENSE` file.
