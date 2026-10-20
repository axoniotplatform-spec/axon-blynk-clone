// Axon IoT Web Console Application Controller

let activeDeviceId = 1;
let currentDashboard = null;
let chartInstance = null;
let telemetryHistory = [];

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[AxonApp] Initializing Web Console...");

  // Setup Bridge Callbacks
  window.shellBridge.setCallbacks({
    onConnectionChanged: (data) => {
      const statusPill = document.getElementById("status-indicator");
      if (statusPill) {
        if (data.status === "CONNECTED") {
          statusPill.innerHTML = `<span class="status-dot"></span> ONLINE`;
          statusPill.style.color = "var(--color-primary)";
        } else {
          statusPill.innerHTML = `<span class="status-dot" style="background:#fe0f00;box-shadow:none;"></span> OFFLINE`;
          statusPill.style.color = "#fe0f00";
        }
      }
    },
    onValueUpdated: (data) => {
      console.log("[AxonApp] Value update received:", data);
      handleLivePinUpdate(data.stream, data.value);
    }
  });

  // Wait 300ms for WebSocket handshake, then load dashboard
  setTimeout(loadDeviceDashboard, 300);
});

async function loadDeviceDashboard() {
  try {
    const data = await window.shellBridge.getDeviceDashboard(activeDeviceId);
    currentDashboard = data;
    console.log("[AxonApp] Dashboard loaded:", data);

    document.getElementById("device-name-heading").innerText = data.deviceName || "ESP32 Controller";
    document.getElementById("device-status-badge").innerText = data.status || "ONLINE";

    renderWidgets(data.widgets, data.datastreams);
    initSuperGraph();
  } catch (err) {
    console.warn("[AxonApp] Bridge load failed, retrying via REST fallback...", err);
    fetch(`/api/v1/devices/${activeDeviceId}/widgets`)
      .then(r => r.json())
      .then(widgets => {
        renderWidgets(widgets, []);
        initSuperGraph();
      });
  }
}

function renderWidgets(widgets, datastreams) {
  const grid = document.getElementById("widget-canvas");
  grid.innerHTML = "";

  widgets.forEach(w => {
    const card = document.createElement("div");
    card.className = "widget-card";
    card.style.gridColumn = `span ${w.grid?.w || 4}`;

    let widgetContent = "";

    if (w.type === "WEB_STYLED_BUTTON") {
      const isOn = String(w.currentValue) === "1";
      widgetContent = `
        <div class="widget-header">
          <span class="widget-title">${w.label || "Button"}</span>
          <span class="widget-pin-badge">${w.pin}</span>
        </div>
        <div class="styled-button-widget">
          <button id="btn-${w.pin}" class="blynk-btn ${isOn ? 'on' : ''}" onclick="toggleButton('${w.pin}')">
            ${isOn ? (w.onLabel || 'ON') : (w.offLabel || 'OFF')}
          </button>
        </div>
      `;
    } else if (w.type === "SLIDER") {
      const min = w.settings?.min ?? 0;
      const max = w.settings?.max ?? 255;
      const step = w.settings?.step ?? 1;
      const val = w.currentValue || 128;

      widgetContent = `
        <div class="widget-header">
          <span class="widget-title">${w.label || "Slider"}</span>
          <span class="widget-pin-badge">${w.pin}</span>
        </div>
        <div class="slider-container">
          <div id="slider-val-${w.pin}" class="slider-val-display">${val}</div>
          <input type="range" class="blynk-slider" min="${min}" max="${max}" step="${step}" value="${val}" 
                 oninput="onSliderChange('${w.pin}', this.value)" />
        </div>
      `;
    } else if (w.type === "GAUGE") {
      const units = w.settings?.units || "°C";
      const val = parseFloat(w.currentValue) || 28.4;
      const percent = Math.min(Math.max((val + 20) / 120, 0), 1);
      const dashoffset = 250 - (percent * 180);

      widgetContent = `
        <div class="widget-header">
          <span class="widget-title">${w.label || "Gauge"}</span>
          <span class="widget-pin-badge">${w.pin}</span>
        </div>
        <div class="gauge-container">
          <svg width="150" height="120" viewBox="0 0 100 80">
            <path d="M 15 70 A 40 40 0 1 1 85 70" fill="none" stroke="#27293d" stroke-width="10" stroke-linecap="round"/>
            <path id="gauge-path-${w.pin}" d="M 15 70 A 40 40 0 1 1 85 70" fill="none" stroke="#d1ff39" stroke-width="10" 
                  stroke-dasharray="250" stroke-dashoffset="${dashoffset}" stroke-linecap="round" style="transition: stroke-dashoffset 0.3s ease;"/>
          </svg>
          <div class="gauge-val">
            <span id="gauge-val-${w.pin}">${val.toFixed(1)}</span>
            <div class="gauge-units">${units}</div>
          </div>
        </div>
      `;
    } else if (w.type === "SUPERGRAPH") {
      widgetContent = `
        <div class="widget-header">
          <span class="widget-title">${w.label || "Telemetry Graph"}</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <div style="font-size:11px;color:var(--text-muted);">LIVE (1s)</div>
            <span class="widget-pin-badge">${w.pin}</span>
          </div>
        </div>
        <div class="chart-container">
          <canvas id="supergraph-canvas" class="chart-canvas"></canvas>
        </div>
      `;
    }

    card.innerHTML = widgetContent;
    grid.appendChild(card);
  });
}

async function toggleButton(pin) {
  const btn = document.getElementById(`btn-${pin}`);
  const isCurrentlyOn = btn.classList.contains("on");
  const nextVal = isCurrentlyOn ? "0" : "1";

  // Optimistic UI update
  btn.classList.toggle("on", !isCurrentlyOn);
  btn.innerText = !isCurrentlyOn ? "ON" : "OFF";

  try {
    await window.shellBridge.sendValue(activeDeviceId, pin, nextVal);
  } catch (err) {
    console.error("[AxonApp] Failed to send pin value:", err);
    btn.classList.toggle("on", isCurrentlyOn);
    btn.innerText = isCurrentlyOn ? "ON" : "OFF";
  }
}

let sliderTimeout = null;
function onSliderChange(pin, value) {
  document.getElementById(`slider-val-${pin}`).innerText = value;
  clearTimeout(sliderTimeout);
  sliderTimeout = setTimeout(async () => {
    try {
      await window.shellBridge.sendValue(activeDeviceId, pin, value);
    } catch (err) {
      console.error("[AxonApp] Slider update failed:", err);
    }
  }, 100);
}

function handleLivePinUpdate(pin, value) {
  // Update button if matches
  const btn = document.getElementById(`btn-${pin}`);
  if (btn) {
    const isOn = String(value) === "1";
    btn.classList.toggle("on", isOn);
    btn.innerText = isOn ? "ON" : "OFF";
  }

  // Update slider if matches
  const sliderVal = document.getElementById(`slider-val-${pin}`);
  if (sliderVal) {
    sliderVal.innerText = value;
  }

  // Update gauge if matches
  const gaugeVal = document.getElementById(`gauge-val-${pin}`);
  const gaugePath = document.getElementById(`gauge-path-${pin}`);
  if (gaugeVal && gaugePath) {
    const num = parseFloat(value) || 0;
    gaugeVal.innerText = num.toFixed(1);
    const percent = Math.min(Math.max((num + 20) / 120, 0), 1);
    const dashoffset = 250 - (percent * 180);
    gaugePath.setAttribute("stroke-dashoffset", dashoffset);
  }

  // Add to telemetry chart
  if (pin === "V2") {
    addChartPoint(parseFloat(value) || 0);
  }
}

function initSuperGraph() {
  const canvas = document.getElementById("supergraph-canvas");
  if (!canvas) return;

  // Generate initial simulated telemetry points around 28C
  telemetryHistory = [];
  const now = Date.now();
  for (let i = 20; i >= 0; i--) {
    telemetryHistory.push({
      time: new Date(now - i * 1000),
      val: 28.0 + (Math.sin(i / 2) * 1.5) + (Math.random() * 0.4)
    });
  }

  drawChart();

  // Simulate live heartbeat temperature fluctuation every 2.5s
  setInterval(() => {
    const lastVal = telemetryHistory[telemetryHistory.length - 1].val;
    const delta = (Math.random() - 0.48) * 0.5;
    const nextVal = Math.min(Math.max(lastVal + delta, 22.0), 35.0);
    addChartPoint(nextVal);
  }, 2500);
}

function addChartPoint(val) {
  telemetryHistory.push({ time: new Date(), val: val });
  if (telemetryHistory.length > 30) telemetryHistory.shift();
  drawChart();
}

function drawChart() {
  const canvas = document.getElementById("supergraph-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  if (telemetryHistory.length < 2) return;

  // Find min/max
  const vals = telemetryHistory.map(p => p.val);
  const min = Math.min(...vals) - 1;
  const max = Math.max(...vals) + 1;

  // Grid lines
  ctx.strokeStyle = "#27293d";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = (h / 4) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw area gradient
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(16, 241, 127, 0.35)");
  grad.addColorStop(1, "rgba(16, 241, 127, 0.0)");

  ctx.beginPath();
  const stepX = w / (telemetryHistory.length - 1);

  telemetryHistory.forEach((p, idx) => {
    const x = idx * stepX;
    const y = h - ((p.val - min) / (max - min)) * (h - 20) - 10;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw Line
  ctx.beginPath();
  ctx.strokeStyle = "#10f17f";
  ctx.lineWidth = 2.5;
  ctx.lineJoin = "round";

  telemetryHistory.forEach((p, idx) => {
    const x = idx * stepX;
    const y = h - ((p.val - min) / (max - min)) * (h - 20) - 10;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Draw latest point dot
  const lastX = (telemetryHistory.length - 1) * stepX;
  const lastY = h - ((telemetryHistory[telemetryHistory.length - 1].val - min) / (max - min)) * (h - 20) - 10;
  ctx.beginPath();
  ctx.arc(lastX, lastY, 5, 0, Math.PI * 2);
  ctx.fillStyle = "#10f17f";
  ctx.fill();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.stroke();
}
