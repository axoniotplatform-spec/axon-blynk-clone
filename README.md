# Axon IoT (Blynk Compatibility Clone)

[![Build Zero-Branding Signed APK & Web](https://github.com/axoniotplatform-spec/axon-blynk-clone/actions/workflows/build_axon_apk.yml/badge.svg)](https://github.com/axoniotplatform-spec/axon-blynk-clone/actions/workflows/build_axon_apk.yml)
[![Download Signed Android APK](https://img.shields.io/badge/Android_APK-Download_Signed_Release-00E5FF?style=flat&logo=android&logoColor=black)](https://github.com/axoniotplatform-spec/axon-blynk-clone/releases/tag/latest-apk)

> **Architectural Differentiation**:
> - **Axon-Blynk Clone** (`https://github.com/axoniotplatform-spec/axon-blynk-clone.git`): This repository. A self-hosted, industrial-grade, drop-in replacement for Blynk Cloud. Features wire-compatible binary framing on TCP port `8080`, external REST APIs (`/external/api/*`), glassmorphic Web & Mobile Operator Clients, RSA-2048 signed Android Release APKs, QR LAN Pairing Hub, Blynk.Air HTTP OTA `.bin` firmware push, cellular GSM/LTE uplink drivers, and real-time telemetry anomaly detection.
> - **First Axon Core** (`https://github.com/axoniotplatform-spec/axon-iot-core.git`): The native Axon IoT core platform and services. Never push clone remediation or compatibility shim code to `axon-iot-core.git`.

---

## Direct Mobile APK Downloads (Zero Third-Party Branding, RSA-2048 Signed)

- **ARM64 Release APK (Recommended for modern Android phones)**: [`Axon-IoT-Mobile-arm64-v8a.apk`](https://github.com/axoniotplatform-spec/axon-blynk-clone/releases/download/latest-apk/Axon-IoT-Mobile-arm64-v8a.apk)
- **ARMv7 Release APK (32-bit Android devices)**: [`Axon-IoT-Mobile-armeabi-v7a.apk`](https://github.com/axoniotplatform-spec/axon-blynk-clone/releases/download/latest-apk/Axon-IoT-Mobile-armeabi-v7a.apk)
- **Universal Release APK**: [`Axon-IoT-Mobile-Universal.apk`](https://github.com/axoniotplatform-spec/axon-blynk-clone/releases/download/latest-apk/Axon-IoT-Mobile-Universal.apk)

---

## Key Features

1. **Dual Transport Ingress & PostgreSQL/TimescaleDB Engine**:
   - **Blynk Binary TCP Engine (Port 8080)**: Full byte-level protocol compatibility supporting standard hardware sketches using official `BlynkSimpleEsp32.h` or native `AxonIoT.h`.
   - **Cloud-Ready REST Telemetry (Port 8000)**: Direct `/external/api/update?token={token}&{pin}={value}` burst support with async micro-batching queue (`backend/telemetry_batcher.py`) and TimescaleDB hypertable support (`backend/migrations/init_timescaledb.sql`).

2. **Glassmorphic Authentication, Mobile App & QR LAN Pairing Hub**:
   - Unified **Sign In** and **Create Enterprise Tenant** workflows across both the Web Console (`/`) and the Mobile Client (`/flutter/` & native Android APK).
   - **📱 Mobile QR & OTA Hub**: Auto-detects host LAN Wi-Fi IP (`/api/v1/system/connect-info`) and renders zero-dependency ISO/IEC 18004 SVG QR codes (`/api/v1/system/qr.svg`) for instant phone pairing.
   - Configurable **Gateway Server Endpoint** right on the mobile login screen with live ping diagnostics.

3. **Blynk.Air-Compatible HTTP OTA Firmware Push (`backend/api/ota.py`)**:
   - Stage `.bin` firmware binaries via Web Console or `POST /api/v1/ota/upload` with automatic `MD5` and `SHA-256` verification.
   - Hardware streaming endpoint `GET /external/api/ota/firmware?token={token}&version={ver}&mcu=ESP32` streams `200 OK` (`x-MD5` & `X-Axon-SHA256` headers) or `304 Not Modified` when up-to-date. Ready-to-flash reference sketch included at `firmware/esp32_axon_ota_client/esp32_axon_ota_client.ino`.

4. **Enterprise Cellular (2G/4G GSM/LTE) & In-App Firmware Studio (`firmware/AxonGSM.h`)**:
   - Supports SIM800L, SIM7600, A7670, and standard GSM modems via TinyGSM with automatic carrier APN negotiation and ESP32 brownout suppression.
   - Built-in `⚡ Firmware Studio` dynamically synthesizes ready-to-flash C++ sketches for ESP32, Pico W, Arduino Uno R4, and ESP8266.

5. **Industrial Anomaly Detection & Multi-Channel Push Alerts**:
   - Real-time detection for `UNEXPECTED_INGRESS_WHILE_INACTIVE`, `VALUE_STALL`, `TOTALIZER_ROLLBACK`, and `DEVICE_HEALTH_SWEEP`.
   - Live Telegram Bot, SMS Gateway, and Discord/Slack Webhook dispatcher (`backend/notification_service.py`) configurable at runtime via `POST /api/v1/notifications/configure`.

---

## Local & Docker Setup

```bash
# Option A: Python Virtual Environment
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_server.py

# Option B: Docker Compose (with TimescaleDB)
docker compose up --build -d
```

- **Web Console**: `http://127.0.0.1:8000/`
- **Mobile Web Client**: `http://127.0.0.1:8000/flutter/`
- **Direct Signed APK Download**: `http://127.0.0.1:8000/downloads/axon-iot.apk`
- **Hardware TCP Gateway**: Port `8080` (Binary Blynk framing)

---

## Automated Verification Suites

```bash
python tests/test_live_simulation_and_anomalies.py
python tests/test_ota_and_connect_suite.py
```
