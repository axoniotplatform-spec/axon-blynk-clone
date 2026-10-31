/*
 * Axon_Hybrid_Dual_Uplink.ino
 * Hybrid Multi-Bearer Gateway: Wi-Fi Primary with Cellular GSM Failover
 * Target: ESP32 / ESP32-S3 + SIM800L / SIM7600
 *
 * Operational Principle:
 * 1. Uses Wi-Fi while within range of local router (zero cellular SIM data cost).
 * 2. If Wi-Fi router loses power, fails, or device is moved out to field, automatically
 *    switches to SIM cellular data uplink (GPRS/LTE).
 * 3. Continuously verifies Wi-Fi availability in background; automatically drops
 *    cellular and switches back to Wi-Fi as soon as network recovers.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "../AxonGSM.h"

// ── AXON CONFIGURATION ──────────────────────────────────────────
#define AXON_DEVICE_TOKEN "YOUR_AXON_DEVICE_TOKEN"
#define AXON_SERVER_HOST  "127.0.0.1"
#define AXON_REST_PORT    8000

// ── WI-FI CREDENTIALS ───────────────────────────────────────────
const char* WIFI_SSID = "Your_WiFi_Network";
const char* WIFI_PASS = "Your_WiFi_Password";

// ── MODEM UART PINS (ESP32) ─────────────────────────────────────
#define SIM_RX_PIN  16
#define SIM_TX_PIN  17
#define SIM_RST_PIN 4

enum UplinkMode {
  UPLINK_WIFI,
  UPLINK_CELLULAR,
  UPLINK_OFFLINE
};

UplinkMode currentUplink = UPLINK_OFFLINE;
unsigned long lastTelemetry = 0;
const unsigned long INTERVAL_MS = 15000;

bool connectWiFi() {
  Serial.print(F("[Hybrid Gateway] Connecting to Wi-Fi: "));
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 8000) {
    delay(500);
    Serial.print(F("."));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[Hybrid Gateway] ✅ Wi-Fi Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    return true;
  }
  Serial.println(F("\n[Hybrid Gateway] ❌ Wi-Fi Connection Failed."));
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println(F("\n======================================================="));
  Serial.println(F("  AXON HYBRID DUAL-UPLINK (WI-FI + CELLULAR FAILOVER)  "));
  Serial.println(F("======================================================="));

  // Initialize Cellular driver in standby
  AxonGSM.begin(AXON_DEVICE_TOKEN, AXON_SERVER_HOST, AXON_REST_PORT, SIM_RX_PIN, SIM_TX_PIN, SIM_RST_PIN);

  // Try Wi-Fi first
  if (connectWiFi()) {
    currentUplink = UPLINK_WIFI;
  } else {
    Serial.println(F("[Hybrid Gateway] Failing over to Cellular GPRS..."));
    if (AxonGSM.connectCellular()) {
      currentUplink = UPLINK_CELLULAR;
    } else {
      currentUplink = UPLINK_OFFLINE;
    }
  }
}

void loop() {
  unsigned long now = millis();

  // Background Wi-Fi Recovery Check
  if (currentUplink == UPLINK_CELLULAR) {
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println(F("[Hybrid Gateway] 🔄 Wi-Fi recovered! Switching back to Wi-Fi to save cellular data."));
      currentUplink = UPLINK_WIFI;
    }
  }

  // Periodic Telemetry Dispatch
  if (now - lastTelemetry >= INTERVAL_MS) {
    lastTelemetry = now;
    float simulatedTemp = 28.5 + (random(0, 100) / 10.0);

    if (currentUplink == UPLINK_WIFI) {
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String("http://") + AXON_SERVER_HOST + ":" + AXON_REST_PORT + 
                     "/external/api/update?token=" + AXON_DEVICE_TOKEN + "&V2=" + String(simulatedTemp, 1);
        http.begin(url);
        int httpCode = http.GET();
        http.end();
        Serial.printf("[Wi-Fi Uplink] Temp V2=%.1f C [HTTP %d]\n", simulatedTemp, httpCode);
      } else {
        Serial.println(F("[Hybrid Gateway] ⚠️ Wi-Fi lost! Auto-activating Cellular failover..."));
        if (AxonGSM.connectCellular()) {
          currentUplink = UPLINK_CELLULAR;
          AxonGSM.virtualWrite(2, simulatedTemp, 1);
        }
      }
    } else if (currentUplink == UPLINK_CELLULAR) {
      Serial.printf("[Cellular Uplink] Temp V2=%.1f C\n", simulatedTemp);
      AxonGSM.virtualWrite(2, simulatedTemp, 1);
    }
  }
}
