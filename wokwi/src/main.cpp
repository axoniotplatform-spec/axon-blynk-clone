#define BLYNK_TEMPLATE_ID "TMPL2yjltoB57"
#define BLYNK_TEMPLATE_NAME "Axon Wokwi Parity"
#define BLYNK_PRINT Serial
#define AXON_TEST_DEVICE_TOKEN __AXON_TEST_DEVICE_TOKEN__

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>

static const char* WIFI_SSID = "Wokwi-GUEST";
static const char* WIFI_PASSWORD = "";
static const char* GATEWAY_HOST = "10.13.37.1";
static const uint16_t GATEWAY_PORT = 8080;

BLYNK_CONNECTED() {
  Serial.println("BLYNK_CONNECTED");
}

void setup() {
  Serial.begin(115200);
  delay(250);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);
  const unsigned long wifiDeadline = millis() + 20000;
  while (WiFi.status() != WL_CONNECTED && millis() < wifiDeadline) {
    delay(250);
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WIFI_CONNECTION_FAILED");
    return;
  }
  Serial.println("WIFI_CONNECTED");

  Blynk.config(AXON_TEST_DEVICE_TOKEN, GATEWAY_HOST, GATEWAY_PORT);
  if (!Blynk.connect(15000)) {
    Serial.println("BLYNK_LOGIN_FAILED");
    return;
  }

  Blynk.virtualWrite(V2, 27.5);
  delay(500);
  Blynk.run();
  Serial.println("V2_TELEMETRY_SENT");
  Serial.println("WOKWI_PARITY_PASS");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    Blynk.run();
  }
  delay(10);
}
