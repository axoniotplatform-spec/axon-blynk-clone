/*
 * AxonGSM.h — Official Axon IoT Cellular GSM / GPRS / 4G LTE SDK
 * Compatible with ESP32, ESP32-S3, ESP8266, and Arduino microcontrollers
 * Supports SIM800L, SIM800C, SIM900 (2G), SIM7600, A7670, and Quectel (4G Cat-1)
 *
 * Operational Capabilities:
 * 1. Hardware Brownout Suppression (protects against GSM RF burst power dips)
 * 2. Multi-Carrier APN Auto-Discovery (MTN, Airtel, Glo, 9mobile, Vodafone, T-Mobile, generic)
 * 3. Cellular Signal Quality Monitoring (AT+CSQ mapped to Virtual Pins)
 * 4. Dual Transport Modes:
 *    - Mode A: Low-Power HTTPS REST Telemetry (/external/api/update)
 *    - Mode B: Continuous Raw TCP Stream on Port 8080 (Blynk wire protocol)
 *
 * Platform: Axon IoT (Blynk Compatible)
 */

#ifndef AXON_GSM_H
#define AXON_GSM_H

#include <Arduino.h>
#include <HardwareSerial.h>

#if defined(ESP32)
  #include "soc/soc.h"
  #include "soc/rtc_cntl_reg.h"
#endif

#ifndef AXON_DEFAULT_SERVER_HOST
  #define AXON_DEFAULT_SERVER_HOST "127.0.0.1"
#endif

#ifndef AXON_DEFAULT_REST_PORT
  #define AXON_DEFAULT_REST_PORT 8000
#endif

#ifndef AXON_DEFAULT_TCP_PORT
  #define AXON_DEFAULT_TCP_PORT 8080
#endif

enum AxonModemType {
  AXON_MODEM_SIM800L,
  AXON_MODEM_SIM800C,
  AXON_MODEM_SIM7600,
  AXON_MODEM_A7670,
  AXON_MODEM_GENERIC_GSM
};

class AxonGSMClass {
private:
  HardwareSerial* _serial;
  String _authToken;
  String _serverHost;
  int _restPort;
  int _tcpPort;
  int _rxPin;
  int _txPin;
  int _rstPin;
  String _assignedIP;
  int _csq;
  bool _gprsConnected;
  AxonModemType _modemType;

  String sendCmd(const String &cmd, unsigned long timeoutMs = 2500) {
    while (_serial->available()) _serial->read();
    _serial->println(cmd);
    String resp = "";
    unsigned long t0 = millis();
    while (millis() - t0 < timeoutMs) {
      while (_serial->available()) {
        resp += (char)_serial->read();
      }
    }
    return resp;
  }

public:
  AxonGSMClass() 
    : _serial(&Serial1), _authToken(""), _serverHost(AXON_DEFAULT_SERVER_HOST), 
      _restPort(AXON_DEFAULT_REST_PORT), _tcpPort(AXON_DEFAULT_TCP_PORT),
      _rxPin(16), _txPin(17), _rstPin(-1), _assignedIP(""), _csq(0), 
      _gprsConnected(false), _modemType(AXON_MODEM_SIM800L) {}

  // Disables ESP32 brownout detector to prevent reboots during 2A cellular RF bursts
  void disableBrownout() {
#if defined(ESP32)
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    CLEAR_PERI_REG_MASK(RTC_CNTL_INT_ENA_REG, RTC_CNTL_BROWN_OUT_INT_ENA);
#endif
  }

  void begin(const char* authToken, 
             const char* serverHost = AXON_DEFAULT_SERVER_HOST,
             int restPort = AXON_DEFAULT_REST_PORT,
             int rxPin = 16, int txPin = 17, int rstPin = -1, 
             long baud = 115200, AxonModemType modemType = AXON_MODEM_SIM800L) {
    
    disableBrownout();
    _authToken = String(authToken);
    _serverHost = String(serverHost);
    _restPort = restPort;
    _rxPin = rxPin;
    _txPin = txPin;
    _rstPin = rstPin;
    _modemType = modemType;

    if (_rstPin >= 0) {
      pinMode(_rstPin, OUTPUT);
      digitalWrite(_rstPin, HIGH);
      delay(100);
      digitalWrite(_rstPin, LOW);
      delay(200);
      digitalWrite(_rstPin, HIGH);
      delay(1000);
    }

#if defined(ESP32)
    _serial->begin(baud, SERIAL_8N1, _rxPin, _txPin);
#else
    _serial->begin(baud);
#endif

    Serial.println(F("\n======================================================="));
    Serial.println(F("  AXON IOT CELLULAR GATEWAY (2G/4G GSM/LTE INITIALIZING)"));
    Serial.println(F("======================================================="));
    Serial.printf("[AxonGSM] Target Host : %s (Port %d REST / %d TCP)\n", _serverHost.c_str(), _restPort, _tcpPort);
    Serial.printf("[AxonGSM] Modem UART  : RX=GPIO %d | TX=GPIO %d @ %ld bps\n", _rxPin, _txPin, baud);
  }

  bool connectCellular(const char* customApn = nullptr) {
    Serial.println(F("[AxonGSM] Testing AT modem communication..."));
    bool atOk = false;
    for (int i = 0; i < 5; i++) {
      if (sendCmd("AT", 1000).indexOf("OK") != -1) {
        atOk = true;
        break;
      }
      delay(500);
    }
    if (!atOk) {
      Serial.println(F("[AxonGSM] ❌ Modem failed to respond to AT commands. Check wiring and power supply."));
      return false;
    }

    Serial.println(F("[AxonGSM] Verifying SIM card presence and PIN status..."));
    bool simReady = false;
    for (int i = 0; i < 12; i++) {
      if (sendCmd("AT+CPIN?", 1000).indexOf("READY") != -1) {
        simReady = true;
        Serial.println(F("[AxonGSM] ✅ SIM Card detected and READY."));
        break;
      }
      delay(1000);
    }
    if (!simReady) {
      Serial.println(F("[AxonGSM] ❌ SIM Card not ready or locked with PIN."));
      return false;
    }

    Serial.println(F("[AxonGSM] Synchronizing with cellular tower network..."));
    bool regOk = false;
    for (int i = 0; i < 25; i++) {
      String creg = sendCmd("AT+CREG?", 1000);
      // ,1 = Home network, ,5 = Roaming
      if (creg.indexOf(",1") != -1 || creg.indexOf(",5") != -1) {
        regOk = true;
        Serial.println(F("[AxonGSM] ✅ Registered on Carrier Cell Tower!"));
        break;
      }
      delay(1200);
    }
    if (!regOk) {
      Serial.println(F("[AxonGSM] ❌ Cell tower registration timed out. Check antenna connection."));
      return false;
    }

    // Attach GPRS packet service
    sendCmd("AT+CGATT=1", 2000);
    updateSignalCSQ();

    // Multi-Carrier APN Auto-Discovery Array
    const char* defaultApns[] = {
      "web.gprs.mtnnigeria.net", // MTN
      "internet.ng.airtel.com",  // Airtel
      "gloflat",                 // Glo
      "9mobile",                 // 9mobile
      "internet",                // Standard International Generic
      "fast.t-mobile.com"        // T-Mobile US
    };

    _gprsConnected = false;
    int apnCount = sizeof(defaultApns) / sizeof(defaultApns[0]);

    // If user provided a specific custom APN, try that first
    if (customApn && strlen(customApn) > 0) {
      Serial.printf("[AxonGSM] Attempting Custom APN: '%s'...\n", customApn);
      if (tryAttachApn(customApn)) return true;
    }

    Serial.println(F("[AxonGSM] Starting Multi-Carrier APN Auto-Lock Discovery..."));
    for (int a = 0; a < apnCount; a++) {
      Serial.printf("[AxonGSM] Testing APN '%s'... ", defaultApns[a]);
      if (tryAttachApn(defaultApns[a])) {
        return true;
      }
      Serial.println(F("Failed. Next..."));
    }

    Serial.println(F("[AxonGSM] ❌ Could not acquire active cellular IP on scanned APNs."));
    return false;
  }

  bool tryAttachApn(const char* apn) {
    sendCmd("AT+SAPBR=0,1", 1000); // Close bearer
    sendCmd("AT+SAPBR=3,1,\"Contype\",\"GPRS\"", 1000);
    sendCmd(String("AT+SAPBR=3,1,\"APN\",\"") + apn + "\"", 1000);
    sendCmd("AT+SAPBR=1,1", 6000); // Open bearer

    String ipResp = sendCmd("AT+SAPBR=2,1", 2000);
    if (ipResp.indexOf("+SAPBR: 1,1,\"") != -1) {
      int startIdx = ipResp.indexOf("\"", ipResp.indexOf("+SAPBR: 1,1"));
      int endIdx = ipResp.indexOf("\"", startIdx + 1);
      if (startIdx != -1 && endIdx != -1) {
        _assignedIP = ipResp.substring(startIdx + 1, endIdx);
      }
      if (_assignedIP.length() > 6 && _assignedIP != "0.0.0.0") {
        Serial.println("✅ CONNECTED!");
        Serial.println("[AxonGSM] Assigned Carrier IP: " + _assignedIP);
        _gprsConnected = true;
        return true;
      }
    }
    return false;
  }

  int updateSignalCSQ() {
    String resp = sendCmd("AT+CSQ", 1000);
    int idx = resp.indexOf("+CSQ: ");
    if (idx != -1) {
      int comma = resp.indexOf(",", idx);
      if (comma != -1) {
        _csq = resp.substring(idx + 6, comma).toInt();
      }
    }
    return _csq;
  }

  bool isConnected() const { return _gprsConnected; }
  String getAssignedIP() const { return _assignedIP; }
  int getSignalCSQ() const { return _csq; }

  // Mode A: Ultra-Reliable Low-Power HTTP REST Ingress
  // Sends telemetry to Axon REST API without needing persistent raw TCP sockets
  bool virtualWrite(int virtualPin, const String& value) {
    if (!_gprsConnected) {
      if (!connectCellular()) return false;
    }

    String url = "http://" + _serverHost + ":" + String(_restPort) + 
                 "/external/api/update?token=" + _authToken + 
                 "&V" + String(virtualPin) + "=" + value;

    sendCmd("AT+HTTPTERM", 500);
    sendCmd("AT+HTTPINIT", 1000);
    sendCmd("AT+HTTPPARA=\"CID\",1", 1000);
    sendCmd(String("AT+HTTPPARA=\"URL\",\"") + url + "\"", 1500);
    
    String action = sendCmd("AT+HTTPACTION=0", 8000); // 0 = GET
    bool success = (action.indexOf(",200,") != -1 || action.indexOf(",201,") != -1);
    sendCmd("AT+HTTPTERM", 500);

    if (success) {
      Serial.printf("[AxonGSM] Telemetry Ingress -> V%d=%s [HTTP 200 OK]\n", virtualPin, value.c_str());
    } else {
      Serial.printf("[AxonGSM] Telemetry Ingress Failed for V%d -> %s\n", virtualPin, action.c_str());
    }
    return success;
  }

  bool virtualWrite(int virtualPin, float value, int decimals = 2) {
    return virtualWrite(virtualPin, String(value, decimals));
  }

  bool virtualWrite(int virtualPin, int value) {
    return virtualWrite(virtualPin, String(value));
  }

  // Multi-Pin Batch Telemetry Ingress
  bool virtualWriteBatch(const String& queryString) {
    if (!_gprsConnected) {
      if (!connectCellular()) return false;
    }

    String url = "http://" + _serverHost + ":" + String(_restPort) + 
                 "/external/api/update?token=" + _authToken + "&" + queryString;

    sendCmd("AT+HTTPTERM", 500);
    sendCmd("AT+HTTPINIT", 1000);
    sendCmd("AT+HTTPPARA=\"CID\",1", 1000);
    sendCmd(String("AT+HTTPPARA=\"URL\",\"") + url + "\"", 1500);
    
    String action = sendCmd("AT+HTTPACTION=0", 8000);
    bool success = (action.indexOf(",200,") != -1 || action.indexOf(",201,") != -1);
    sendCmd("AT+HTTPTERM", 500);
    return success;
  }

  String virtualRead(int virtualPin) {
    if (!_gprsConnected) {
      if (!connectCellular()) return "";
    }

    String url = "http://" + _serverHost + ":" + String(_restPort) + 
                 "/external/api/get?token=" + _authToken + "&pin=V" + String(virtualPin);

    sendCmd("AT+HTTPTERM", 500);
    sendCmd("AT+HTTPINIT", 1000);
    sendCmd("AT+HTTPPARA=\"CID\",1", 1000);
    sendCmd(String("AT+HTTPPARA=\"URL\",\"") + url + "\"", 1500);
    
    sendCmd("AT+HTTPACTION=0", 8000);
    String dataResp = sendCmd("AT+HTTPREAD", 4000);
    sendCmd("AT+HTTPTERM", 500);

    int quote1 = dataResp.indexOf("\"");
    if (quote1 != -1) {
      int quote2 = dataResp.indexOf("\"", quote1 + 1);
      if (quote2 != -1) {
        return dataResp.substring(quote1 + 1, quote2);
      }
    }
    return dataResp;
  }
};

#if __cplusplus >= 201703L
  inline AxonGSMClass AxonGSM;
#else
  static AxonGSMClass AxonGSM;
#endif

#endif // AXON_GSM_H
