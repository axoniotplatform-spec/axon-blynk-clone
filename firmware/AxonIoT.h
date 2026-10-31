/*
 * AxonIoT.h — Official Axon Native Firmware SDK Header
 * Compatible with ESP32, ESP8266, Raspberry Pi Pico W, Arduino, and STM32
 *
 * Provides Axon Native naming ergonomics while guaranteeing 100% binary wire 
 * compatibility with Blynk port 8080 gateways and existing hardware libraries.
 *
 * Usage:
 *   #include <AxonIoT.h>
 *   
 *   AXON_WRITE(V3) {
 *     int relayState = param.asInt();
 *     digitalWrite(RELAY_PIN, relayState);
 *   }
 *   
 *   void setup() {
 *     Axon.begin(AXON_DEVICE_TOKEN, "WiFi_SSID", "WiFi_PASS", "axon.server.com", 8080);
 *   }
 *   
 *   void loop() {
 *     Axon.run();
 *   }
 */

#ifndef AXON_IOT_H
#define AXON_IOT_H

#if defined(ESP32)
  #include <WiFi.h>
  #include <WiFiClient.h>
  #include <BlynkSimpleEsp32.h>
#elif defined(ESP8266)
  #include <ESP8266WiFi.h>
  #include <BlynkSimpleEsp8266.h>
#elif defined(ARDUINO_ARCH_RP2040)
  #include <WiFi.h>
  #include <BlynkSimpleRP2040W.h>
#else
  #include <BlynkSimpleStream.h>
#endif

// ── Native Axon Naming Aliases ──────────────────────────────────
#define Axon Blynk
#define AXON_WRITE(pin)        BLYNK_WRITE(pin)
#define AXON_READ(pin)         BLYNK_READ(pin)
#define AXON_CONNECTED()       BLYNK_CONNECTED()
#define AXON_DISCONNECTED()    BLYNK_DISCONNECTED()
#define AXON_APP_CONNECTED()   BLYNK_APP_CONNECTED()
#define AXON_APP_DISCONNECTED() BLYNK_APP_DISCONNECTED()

#define AXON_VIRTUAL_WRITE(pin, val) Blynk.virtualWrite(pin, val)

#endif // AXON_IOT_H
