# SunCloud Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz/docs/faq/custom_repositories) 
[![GitHub Stars](https://img.shields.io/github/stars/jsanchezdelvillar/Suncloud_monitor?style=flat-square)](https://github.com/jsanchezdelvillar/Suncloud_monitor/stargazers)
[![Latest Release](https://img.shields.io/github/v/release/jsanchezdelvillar/Suncloud_monitor?style=flat-square)](https://github.com/jsanchezdelvillar/Suncloud_monitor/releases)
[![License](https://img.shields.io/github/license/jsanchezdelvillar/Suncloud_monitor?style=flat-square)](https://github.com/jsanchezdelvillar/Suncloud_monitor/blob/main/LICENSE)

This custom integration allows real-time monitoring of Sungrow (Sunshine Cloud) plants via open API endpoints.  
🧠 Includes token-based auth, ps_key retrieval, plant + device discovery, real-time polling, and automatic recovery.

## Features

- Login + token management
- ps_key, device_sn, plant ID discovery
- `getDeviceRealTimeData` support
- Sensor + input_select entities
- Configurable via UI

## Setup

1. Drop into `custom_components/`
2. Restart HA
3. Go to **Settings > Devices & Services > Add Integration**
4. Search for `SunCloud Monitor` and enter credentials
