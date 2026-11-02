/*
 * ============================================================================
 * AXON IOT — ESP32 BLYNK TCP GATEWAY + BLYNK.AIR HTTP OTA CLIENT
 * ============================================================================
 * Connects simultaneously to:
 *   1. Axon IoT Blynk Binary TCP Gateway (Port 8080) for sub-10ms Virtual Pins
 *   2. Axon IoT HTTP OTA Server (/external/api/ota/check) for zero-touch .bin
 *      firmware upgrades with MD5 verification!
 */

#define BLYNK_TEMPLATE_ID   "TMPL2yjltoB57"
#define BLYNK_TEMPLATE_NAME "BLINKING LED"
#define BLYNK_FIRMWARE_VERSION "1.0.0"
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <BlynkSimpleEsp32.h>

char ssid[] = "YOUR_WIFI_SSID";
char pass[] = "YOUR_WIFI_PASSWORD";
char auth[] = "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk";

// Replace with your Axon IoT Server LAN IP or Cloud Hostname
const char* AXON_HOST      = "192.168.1.50";
const uint16_t AXON_TCP_PORT  = 8080;
const uint16_t AXON_HTTP_PORT = 8000;

BlynkTimer timer;

void checkAxonOTA() {
  WiFiClient client;
  String otaUrl = String("http://") + AXON_HOST + ":" + String(AXON_HTTP_PORT) +
                  "/external/api/ota/firmware?token=" + String(auth) +
                  "&version=" + String(BLYNK_FIRMWARE_VERSION) + "&mcu=ESP32";

  Serial.println("[Axon OTA] Checking for firmware update: " + otaUrl);
  t_httpUpdate_return ret = httpUpdate.update(client, otaUrl, BLYNK_FIRMWARE_VERSION);

  switch (ret) {
    case HTTP_UPDATE_FAILED:
      Serial.printf("[Axon OTA] Error (%d): %s\n", httpUpdate.getLastError(), httpUpdate.getLastErrorString().c_str());
      break;
    case HTTP_UPDATE_NO_UPDATES:
      Serial.println("[Axon OTA] Firmware is up to date (v" BLYNK_FIRMWARE_VERSION ").");
      break;
    case HTTP_UPDATE_OK:
      Serial.println("[Axon OTA] Update installed! Rebooting...");
      break;
  }
}

BLYNK_WRITE(V0) {
  int ledState = param.asInt();
  digitalWrite(2, ledState ? HIGH : LOW);
  Serial.printf("[Axon Pin V0] LED Power -> %d\n", ledState);
}

void pushTelemetry() {
  float simulatedTemp = 26.5 + (random(-15, 25) / 10.0);
  Blynk.virtualWrite(V2, simulatedTemp);
  Blynk.virtualWrite(V99, WiFi.RSSI());
}

void setup() {
  pinMode(2, OUTPUT);
  Serial.begin(115200);
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\n[Axon IoT] WiFi connected! Connecting to TCP Gateway...");

  Blynk.config(auth, AXON_HOST, AXON_TCP_PORT);
  Blynk.connect();

  // Push telemetry every 5s, check OTA updates every 60s
  timer.setInterval(5000L, pushTelemetry);
  timer.setInterval(60000L, checkAxonOTA);
}

void loop() {
  Blynk.run();
  timer.run();
}
