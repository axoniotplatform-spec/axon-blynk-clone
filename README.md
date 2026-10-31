# Axon IoT (Blynk Compatibility Clone)

> **Architectural Differentiation**:
> - **Axon-Blynk Clone** (`https://github.com/axoniotplatform-spec/axon-blynk-clone.git`): This repository. A self-hosted, industrial-grade, drop-in replacement for Blynk Cloud. Features wire-compatible binary framing on TCP port `8080`, external REST APIs (`/external/api/*`), web console, mobile companion UI, In-App Firmware Studio, cellular GSM/LTE uplink drivers, and real-time telemetry anomaly detection.
> - **First Axon Core** (`https://github.com/axoniotplatform-spec/axon-iot-core.git`): The native Axon IoT core platform and services. Never push clone remediation or compatibility shim code to `axon-iot-core.git`.

---

## Key Features

1. **Dual Transport Ingress**:
   - **Blynk Binary TCP Engine (Port 8080)**: Full byte-level protocol compatibility supporting standard hardware sketches using official `BlynkSimpleEsp32.h` or native `AxonIoT.h`.
   - **Cloud-Ready REST Telemetry (Port 8000)**: Direct `/external/api/update?token={token}&{pin}={value}` burst support for cloud environments (such as Render) that drop raw TCP sockets.

2. **Enterprise Cellular (2G/4G GSM/LTE) & Hybrid Dual-Uplink (`firmware/AxonGSM.h`)**:
   - Supports SIM800L, SIM7600, A7670, and standard GSM modems via TinyGSM.
   - Auto-negotiation of mobile carrier APNs (MTN, Airtel, Glo, 9mobile).
   - ESP32 brownout detector suppression (`WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0)`) preventing reset loops during 2A RF transmission bursts.
   - Real-time cellular signal strength (CSQ) mapping to virtual pins.
   - Automatic failover between primary Wi-Fi and fallback Cellular SIM uplink.

3. **In-App Firmware Studio**:
   - Built into the Web Console (`⚡ Firmware Studio`).
   - Dynamically synthesizes ready-to-flash C++ sketches for:
     - **Hardware**: ESP32, Raspberry Pi Pico W, Arduino Uno R4 / Nano ESP32, ESP8266.
     - **Transports**: Wi-Fi, Cellular SIM800L/SIM7600, Hybrid Dual-Uplink.
   - One-click clipboard copy with pre-filled device authentication tokens.

4. **Industrial Anomaly & Audit Engine**:
   - Real-time fault detection evaluated on every telemetry ingress packet:
     - `UNEXPECTED_INGRESS_WHILE_INACTIVE`: Device streaming while marked inactive.
     - `VALUE_STALL`: Sensor reporting constant frozen readings over sustained window.
     - `TOTALIZER_ROLLBACK`: Monotonic pulse/energy counters dropping unexpectedly.
     - `DEVICE_HEALTH_SWEEP`: Sudden dropouts or erratic RSSI/brownout signals.
   - REST Endpoints:
     - `GET /api/v1/anomalies` - List active anomaly alerts.
     - `POST /api/v1/anomalies/{alert_id}/resolve` - Mark alert resolved with audit trail.
     - `GET /api/v1/audit` - Inspect enterprise audit log.
     - `POST /api/v1/audit/log` - Log operational and configuration events.

5. **Multi-Tenant RBAC & Actuator Safety ("View As")**:
   - Live role simulation banner: Superadmin, Tenant Admin, Field Operator, and Read-Only Observer.
   - Automatic actuator control suppression in Read-Only Observer mode to prevent accidental relay switching.
   - Automatic audit logging on every role switch.

---

## Local Setup

```bash
# Set up Python virtual environment
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium

# Launch Axon IoT Services
export DATABASE_URL="sqlite:///$(pwd)/axon_iot.db"
export AXON_CORS_ORIGINS="http://127.0.0.1:8000,http://localhost:8000"
python run_server.py
```

- **Web Console**: `http://127.0.0.1:8000/`
- **Mobile Companion App**: `http://127.0.0.1:8000/app.html`
- **Hardware TCP Gateway**: Port `8080` (Binary Blynk framing)
- **REST & Anomaly API**: Port `8000`

---

## Verification & Automated Test Suite

Run the full end-to-end verification suite:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\verify_axon_all.ps1
```

Verification covers 5 comprehensive stages:
1. Service Port Reachability (HTTP `8000`, Blynk TCP `8080`, Wokwi `9011`).
2. Backend HTTP routes and cloud user directory synchronization.
3. Automations Engine & threshold rule evaluation (e.g., $V2 > 30^\circ\text{C} \rightarrow V3\text{ ON}$).
4. Byte-level raw TCP binary protocol probe (login, ping, telemetry stream, socket disconnect cleanup).
5. ESP32 official PlatformIO firmware compilation (`firmware.bin`).

---

## Production Configuration

Enable authenticated sessions and token redaction:

```bash
export AXON_REQUIRE_AUTH=true
export AXON_EXPOSE_DEVICE_TOKENS=false
export AXON_SEED_PASSWORD="use-a-secret-bootstrap-password"
```

Authenticate via `POST /api/v1/auth/login` and pass `Authorization: Bearer <token>` in API requests. Device external endpoints authenticate with per-device hardware tokens.
