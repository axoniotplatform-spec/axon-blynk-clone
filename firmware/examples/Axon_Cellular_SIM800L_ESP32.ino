/*
 * Axon_Cellular_SIM800L_ESP32.ino
 * Pure Cellular 2G/4G GSM Telemetry Ingress to Axon IoT Core
 * Target: ESP32 / ESP32-S3 + SIM800L or SIM7600
 *
 * Operational Behavior:
 * 1. Automatically initializes SIM800L / SIM7600 over Hardware UART.
 * 2. Suppresses brownouts to withstand GSM 2A current bursts.
 * 3. Scans and auto-locks multi-carrier APNs (MTN, Airtel, Glo, 9mobile).
 * 4. Pushes periodic telemetry bursts to Axon Core REST API (/external/api/update).
 * 5. Works over any network (local LAN, public VPS, Render cloud) without raw TCP port gating.
 */

#include <Arduino.h>
#include "../AxonGSM.h"

// ── AXON CONFIGURATION ──────────────────────────────────────────
#define AXON_DEVICE_TOKEN "YOUR_AXON_DEVICE_TOKEN"
#define AXON_SERVER_HOST  "127.0.0.1" // Or your public cloud IP / domain
#define AXON_REST_PORT    8000

// ── MODEM UART PINS (ESP32) ─────────────────────────────────────
#define SIM_RX_PIN  16 // ESP32 RX2 <- SIM800L TXD
#define SIM_TX_PIN  17 // ESP32 TX2 -> SIM800L RXD
#define SIM_RST_PIN 4  // Optional reset pin (-1 if unassigned)

// ── HARDWARE SENSORS ────────────────────────────────────────────
#define SENSOR_PIN_TEMP 34
#define SENSOR_PIN_FLOW 35

unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 15000; // Send telemetry every 15s

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println(F("\n=================================================="));
  Serial.println(F("  AXON CELLULAR IOT — SIM800L TELEMETRY CLIENT   "));
  Serial.println(F("=================================================="));

  // 1. Initialize Axon Cellular Driver
  AxonGSM.begin(AXON_DEVICE_TOKEN, AXON_SERVER_HOST, AXON_REST_PORT, SIM_RX_PIN, SIM_TX_PIN, SIM_RST_PIN);

  // 2. Connect to Cellular GPRS / LTE
  if (AxonGSM.connectCellular()) {
    Serial.println(F("✅ Cellular data uplink established successfully!"));
  } else {
    Serial.println(F("❌ Cellular connection failed. Retrying in background..."));
  }
}

void loop() {
  unsigned long now = millis();

  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = now;

    // Read analog/digital sensors
    float simulatedTemp = 25.0 + (random(0, 150) / 10.0); // Simulated temperature (25.0°C - 40.0°C)
    int simulatedPulseCount = random(10, 50);              // Simulated flow pulses

    Serial.printf("\n[Sensor Read] Temp: %.1f C | Pulses: %d\n", simulatedTemp, simulatedPulseCount);

    // 1. Send Temperature to Virtual Pin V2
    AxonGSM.virtualWrite(2, simulatedTemp, 1);

    // 2. Send Cellular Signal Quality (CSQ) to Virtual Pin V10
    int csq = AxonGSM.getSignalCSQ();
    AxonGSM.virtualWrite(10, csq);

    // 3. Read Actuator Control State (e.g. Fan Relay V3)
    String relayState = AxonGSM.virtualRead(3);
    Serial.printf("[Axon Cloud Actuator Read] Relay V3 State: %s\n", relayState.c_str());
  }
}
