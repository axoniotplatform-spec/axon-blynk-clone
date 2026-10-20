/**
 * Axon IoT ShellBridge - Pure JavaScript Implementation
 * 1:1 Protocol-compatible with Blynk cloud.blynk Native ShellBridge
 */
class AxonShellBridge {
  constructor(wsUrl = null) {
    this.wsUrl = wsUrl || `ws://${window.location.host}/ws`;
    this.ws = null;
    this.pending = new Map();
    this.callbacks = {};
    this.nextId = 0;
    this.connected = false;
    this.reconnectTimer = null;

    this.connect();
  }

  connect() {
    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        console.log("[AxonBridge] Connected to IoT Core Gateway");
        this.connected = true;
        this.emit("onConnectionChanged", { status: "CONNECTED" });
      };

      this.ws.onclose = () => {
        console.warn("[AxonBridge] Connection lost, reconnecting in 2s...");
        this.connected = false;
        this.emit("onConnectionChanged", { status: "DISCONNECTED" });
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => this.connect(), 2000);
      };

      this.ws.onerror = (err) => {
        console.error("[AxonBridge] WebSocket error:", err);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          // Check if it's an event broadcast (e.g. onValueUpdated)
          if (msg.event) {
            this.emit(msg.event, msg.data);
            return;
          }

          // Otherwise it's an RPC response
          if (msg.id && this.pending.has(String(msg.id))) {
            const { resolve, reject, timer } = this.pending.get(String(msg.id));
            clearTimeout(timer);
            this.pending.delete(String(msg.id));

            if (msg.error) {
              reject(new Error(msg.error.message || "RPC Error"));
            } else {
              resolve(msg.result);
            }
          }
        } catch (e) {
          console.error("[AxonBridge] Message parse error:", e);
        }
      };
    } catch (e) {
      console.error("[AxonBridge] Connection failure:", e);
      setTimeout(() => this.connect(), 3000);
    }
  }

  emit(name, value) {
    if (typeof this.callbacks[name] === "function") {
      try {
        this.callbacks[name](value);
      } catch (e) {
        console.error(`[AxonBridge] Callback error for ${name}:`, e);
      }
    }
  }

  setCallbacks(cbs) {
    Object.assign(this.callbacks, cbs);
  }

  call(method, params = {}) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
        return reject(new Error("Bridge not connected to Axon Gateway"));
      }

      const id = String(++this.nextId);
      const payload = JSON.stringify({ id, method, params });

      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Request ${method} timed out`));
      }, 10000);

      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(payload);
    });
  }

  // 1:1 Blynk RPC Methods
  getDevices(options = {}) {
    return this.call("getDevices", { options });
  }

  getDevice(selector) {
    return this.call("getDevice", { selector });
  }

  getDeviceDashboard(deviceId) {
    return this.call("getDeviceDashboard", { deviceId });
  }

  sendValue(deviceId, stream, value) {
    return this.call("sendValue", { deviceId, stream, value });
  }

  getHistoryData(options) {
    return this.call("getHistoryData", { options });
  }

  getTheme() {
    return this.call("getTheme");
  }
}

// Attach to window globally as window.shellBridge
window.shellBridge = new AxonShellBridge();
