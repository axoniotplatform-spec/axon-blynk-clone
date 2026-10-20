// Axon IoT Web Console Application Controller - Full Widget Suite

let activeDeviceId = 1;
let currentDashboard = null;
let telemetryHistory = [];

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[AxonApp] Initializing Web Console...");

  window.shellBridge.setCallbacks({
    onConnectionChanged: (data) => {
      const statusPill = document.getElementById("device-row-status");
      if (statusPill) {
        if (data.status === "CONNECTED") {
          statusPill.className = "status-badge online";
          statusPill.innerHTML = `<span class="status-dot-sm"></span> Online`;
        } else {
          statusPill.className = "status-badge";
          statusPill.innerHTML = `<span class="status-dot-sm"></span> Inactive`;
        }
      }
    },
    onValueUpdated: (data) => {
      console.log("[AxonApp] Live update received:", data);
      handleLivePinUpdate(data.stream, data.value);
    }
  });

  setTimeout(loadDeviceDashboard, 300);
});

async function loadDeviceDashboard() {
  try {
    const data = await window.shellBridge.getDeviceDashboard(activeDeviceId);
    currentDashboard = data;
    renderWidgets(data.widgets, data.datastreams);
    initSuperGraph();
  } catch (err) {
    console.warn("[AxonApp] Bridge load error, falling back to REST API:", err);
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
  if (!grid) return;
  grid.innerHTML = "";

  widgets.forEach(w => {
    const card = document.createElement("div");
    card.className = "table-card";
    card.style.padding = "20px";
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.gridColumn = `span ${w.grid?.w || 4}`;

    const wType = w.widgetType || w.type;
    let widgetContent = "";

    if (wType === "WEB_STYLED_BUTTON") {
      const isOn = String(w.currentValue) === "1";
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;flex:1;min-height:100px;">
          <button id="btn-${w.pin}" class="blynk-btn ${isOn ? 'on' : ''}" onclick="toggleButton('${w.pin}')"
                  style="width:84px;height:84px;border-radius:50%;border:4px solid ${isOn ? '#0375de' : '#fe0f00'};background:${isOn ? 'rgba(3,117,222,0.15)' : 'rgba(254,15,0,0.1)'};color:${isOn ? '#0375de' : '#fe0f00'};font-size:16px;font-weight:800;cursor:pointer;transition:all 0.2s;">
            ${isOn ? 'ON' : 'OFF'}
          </button>
        </div>
      `;
    } else if (wType === "SLIDER") {
      const min = w.settings?.min ?? 0;
      const max = w.settings?.max ?? 255;
      const step = w.settings?.step ?? 1;
      const val = w.currentValue || 128;

      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;flex:1;justify-content:center;">
          <div id="slider-val-${w.pin}" style="font-size:26px;font-weight:800;text-align:center;color:#10f17f;">${val}</div>
          <input type="range" min="${min}" max="${max}" step="${step}" value="${val}" 
                 style="width:100%;accent-color:#10f17f;cursor:pointer;"
                 oninput="onSliderChange('${w.pin}', this.value)" />
        </div>
      `;
    } else if (wType === "GAUGE") {
      const units = w.settings?.units || "°C";
      const val = parseFloat(w.currentValue) || 28.4;
      const percent = Math.min(Math.max((val + 20) / 120, 0), 1);
      const dashoffset = 220 - (percent * 160);

      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;">
          <svg width="130" height="90" viewBox="0 0 100 70">
            <path d="M 15 60 A 35 35 0 1 1 85 60" fill="none" stroke="#e6ecf0" stroke-width="8" stroke-linecap="round"/>
            <path id="gauge-path-${w.pin}" d="M 15 60 A 35 35 0 1 1 85 60" fill="none" stroke="#e0ff7b" stroke-width="8" 
                  stroke-dasharray="220" stroke-dashoffset="${dashoffset}" stroke-linecap="round" style="transition: stroke-dashoffset 0.3s ease;"/>
          </svg>
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-40%);text-align:center;">
            <div id="gauge-val-${w.pin}" style="font-size:22px;font-weight:800;">${val.toFixed(1)}</div>
            <div style="font-size:11px;color:var(--text-muted);">${units}</div>
          </div>
        </div>
      `;
    } else if (wType === "SWITCH") {
      const isOn = String(w.currentValue) === "1";
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;flex:1;">
          <label style="position:relative;display:inline-block;width:56px;height:30px;cursor:pointer;">
            <input type="checkbox" id="switch-${w.pin}" ${isOn ? 'checked' : ''} onchange="toggleSwitch('${w.pin}', this.checked)" style="opacity:0;width:0;height:0;">
            <span style="position:absolute;top:0;left:0;right:0;bottom:0;background-color:${isOn ? '#10f17f' : '#ccc'};border-radius:30px;transition:.3s;">
              <span id="knob-${w.pin}" style="position:absolute;content:'';height:22px;width:22px;left:${isOn ? '30px' : '4px'};bottom:4px;background-color:white;border-radius:50%;transition:.3s;box-shadow:0 2px 4px rgba(0,0,0,0.2);"></span>
            </span>
          </label>
          <span id="switch-lbl-${w.pin}" style="font-weight:700;font-size:14px;color:${isOn ? '#10f17f' : '#8b98a5'};">${isOn ? 'ON' : 'OFF'}</span>
        </div>
      `;
    } else if (wType === "NUMBER_INPUT") {
      const val = parseFloat(w.currentValue) || 24.0;
      const step = w.settings?.step || 0.5;
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:16px;flex:1;">
          <button onclick="stepNumber('${w.pin}', -${step})" style="width:36px;height:36px;border-radius:6px;border:1px solid #d0d7de;background:#fff;font-size:18px;cursor:pointer;font-weight:700;">-</button>
          <div id="stepper-val-${w.pin}" style="font-size:24px;font-weight:800;color:#0375de;min-width:60px;text-align:center;">${val.toFixed(1)}</div>
          <button onclick="stepNumber('${w.pin}', ${step})" style="width:36px;height:36px;border-radius:6px;border:1px solid #d0d7de;background:#fff;font-size:18px;cursor:pointer;font-weight:700;">+</button>
        </div>
      `;
    } else if (wType === "RADIAL_GAUGE") {
      const val = parseInt(w.currentValue) || 62;
      const offset = 180 - (val / 100 * 180);
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;position:relative;flex:1;">
          <svg width="100" height="100" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="30" stroke="#e6ecf0" stroke-width="6" fill="none"/>
            <circle id="radial-circ-${w.pin}" cx="40" cy="40" r="30" stroke="#38f394" stroke-width="6" fill="none"
                    stroke-dasharray="188" stroke-dashoffset="${offset}" stroke-linecap="round" transform="rotate(-90 40 40)"/>
          </svg>
          <div style="position:absolute;text-align:center;">
            <div id="radial-val-${w.pin}" style="font-size:18px;font-weight:800;">${val}%</div>
            <div style="font-size:10px;color:var(--text-muted);">RH</div>
          </div>
        </div>
      `;
    } else if (wType === "LED") {
      const isOn = String(w.currentValue) === "1";
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;flex:1;">
          <div id="led-indicator-${w.pin}" style="width:40px;height:40px;border-radius:50%;background:${isOn ? '#fe0f00' : '#d0d7de'};box-shadow:${isOn ? '0 0 16px #fe0f00' : 'none'};transition:all .3s;"></div>
          <span id="led-status-${w.pin}" style="font-size:12px;font-weight:700;color:${isOn ? '#fe0f00' : '#8b98a5'};">${isOn ? 'ALARM ACTIVE' : 'NORMAL'}</span>
        </div>
      `;
    } else if (wType === "SUPERGRAPH") {
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
          <div>
            <span style="font-weight:600;font-size:14px;color:var(--text-main);">${w.label}</span>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">Real-time Telemetry Stream • 1Hz Sampling</div>
          </div>
          <div style="display:flex;gap:6px;align-items:center;">
            <div class="segmented-pill-group" style="font-size:11px;">
              <div class="segmented-pill active">1h</div>
              <div class="segmented-pill">6h</div>
              <div class="segmented-pill">1d</div>
              <div class="segmented-pill">1w</div>
            </div>
            <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
          </div>
        </div>
        <div style="width:100%;height:180px;position:relative;">
          <canvas id="supergraph-canvas" style="width:100%;height:100%;"></canvas>
        </div>
      `;
    } else if (wType === "TERMINAL") {
      widgetContent = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <span style="font-weight:600;font-size:13.5px;color:var(--text-main);">${w.label}</span>
          <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">${w.pin}</span>
        </div>
        <div style="display:flex;flex-direction:column;flex:1;background:#0d1117;border-radius:6px;padding:10px;font-family:monospace;font-size:11.5px;color:#c9d1d9;">
          <div id="term-log-${w.pin}" style="flex:1;min-height:100px;max-height:140px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;">
            <div>[08:00:01] ESP32 Boot OK. Blynk v1.3.5</div>
            <div>[08:00:02] Connected to WiFi (RSSI: -58dBm)</div>
            <div>[08:00:03] Virtual pins V0-V8 mapped. Ready.</div>
          </div>
          <div style="display:flex;gap:6px;margin-top:8px;border-top:1px solid #21262d;padding-top:6px;">
            <span style="color:#10f17f;">&gt;</span>
            <input type="text" id="term-input-${w.pin}" placeholder="Send command..." 
                   onkeydown="if(event.key==='Enter') sendTerminalCmd('${w.pin}')"
                   style="flex:1;background:transparent;border:none;outline:none;color:#58a6ff;font-family:monospace;font-size:11.5px;" />
          </div>
        </div>
      `;
    }

    card.innerHTML = widgetContent;
    grid.appendChild(card);
  });
}

// Widget Handlers
async function toggleButton(pin) {
  const btn = document.getElementById(`btn-${pin}`);
  const isCurrentlyOn = btn.innerText === "ON";
  const nextVal = isCurrentlyOn ? "0" : "1";

  btn.style.borderColor = !isCurrentlyOn ? "#0375de" : "#fe0f00";
  btn.style.color = !isCurrentlyOn ? "#0375de" : "#fe0f00";
  btn.style.background = !isCurrentlyOn ? "rgba(3,117,222,0.15)" : "rgba(254,15,0,0.1)";
  btn.innerText = !isCurrentlyOn ? "ON" : "OFF";

  await window.shellBridge.sendValue(activeDeviceId, pin, nextVal);
}

async function toggleSwitch(pin, checked) {
  const val = checked ? "1" : "0";
  const lbl = document.getElementById(`switch-lbl-${pin}`);
  const knob = document.getElementById(`knob-${pin}`);
  if (lbl) {
    lbl.innerText = checked ? "ON" : "OFF";
    lbl.style.color = checked ? "#10f17f" : "#8b98a5";
  }
  if (knob) {
    knob.style.left = checked ? "30px" : "4px";
    knob.parentElement.style.backgroundColor = checked ? "#10f17f" : "#ccc";
  }
  await window.shellBridge.sendValue(activeDeviceId, pin, val);
}

let sliderTimeout = null;
function onSliderChange(pin, value) {
  document.getElementById(`slider-val-${pin}`).innerText = value;
  clearTimeout(sliderTimeout);
  sliderTimeout = setTimeout(() => {
    window.shellBridge.sendValue(activeDeviceId, pin, value);
  }, 80);
}

async function stepNumber(pin, delta) {
  const display = document.getElementById(`stepper-val-${pin}`);
  const current = parseFloat(display.innerText) || 24.0;
  const nextVal = (current + delta).toFixed(1);
  display.innerText = nextVal;
  await window.shellBridge.sendValue(activeDeviceId, pin, nextVal);
}

async function sendTerminalCmd(pin) {
  const input = document.getElementById(`term-input-${pin}`);
  const log = document.getElementById(`term-log-${pin}`);
  const cmd = input.value.trim();
  if (!cmd) return;

  const row = document.createElement("div");
  row.style.color = "#58a6ff";
  row.innerText = `> ${cmd}`;
  log.appendChild(row);

  const echo = document.createElement("div");
  echo.style.color = "#7ee787";
  echo.innerText = `OK [${cmd.toUpperCase()}] executed.`;
  log.appendChild(echo);
  log.scrollTop = log.scrollHeight;

  input.value = "";
  await window.shellBridge.sendValue(activeDeviceId, pin, cmd);
}

function handleLivePinUpdate(pin, value) {
  if (pin === "V0") {
    const btn = document.getElementById("btn-V0");
    if (btn) {
      const isOn = String(value) === "1";
      btn.style.borderColor = isOn ? "#0375de" : "#fe0f00";
      btn.style.color = isOn ? "#0375de" : "#fe0f00";
      btn.style.background = isOn ? "rgba(3,117,222,0.15)" : "rgba(254,15,0,0.1)";
      btn.innerText = isOn ? "ON" : "OFF";
    }
  } else if (pin === "V1") {
    const s = document.getElementById("slider-val-V1");
    if (s) s.innerText = value;
  } else if (pin === "V2") {
    const num = parseFloat(value) || 28.4;
    const g = document.getElementById("gauge-val-V2");
    const p = document.getElementById("gauge-path-V2");
    if (g && p) {
      g.innerText = num.toFixed(1);
      const percent = Math.min(Math.max((num + 20) / 120, 0), 1);
      p.setAttribute("stroke-dashoffset", 220 - (percent * 160));
    }
    addChartPoint(num);
  } else if (pin === "V3") {
    const sw = document.getElementById("switch-V3");
    if (sw) sw.checked = String(value) === "1";
  }
}

function initSuperGraph() {
  const canvas = document.getElementById("supergraph-canvas");
  if (!canvas) return;

  telemetryHistory = [];
  const now = Date.now();
  for (let i = 25; i >= 0; i--) {
    telemetryHistory.push({
      time: new Date(now - i * 1000),
      val: 28.0 + (Math.sin(i / 3) * 1.8) + (Math.random() * 0.3)
    });
  }

  drawChart();

  setInterval(() => {
    const last = telemetryHistory[telemetryHistory.length - 1].val;
    const nextVal = Math.min(Math.max(last + ((Math.random() - 0.49) * 0.4), 20.0), 36.0);
    addChartPoint(nextVal);
  }, 2000);
}

function addChartPoint(val) {
  telemetryHistory.push({ time: new Date(), val: val });
  if (telemetryHistory.length > 35) telemetryHistory.shift();
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

  const vals = telemetryHistory.map(p => p.val);
  const min = Math.min(...vals) - 1;
  const max = Math.max(...vals) + 1;

  ctx.strokeStyle = "#f0f2f5";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const y = (h / 3) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(16, 241, 127, 0.25)");
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

  ctx.beginPath();
  ctx.strokeStyle = "#10f17f";
  ctx.lineWidth = 2.5;

  telemetryHistory.forEach((p, idx) => {
    const x = idx * stepX;
    const y = h - ((p.val - min) / (max - min)) * (h - 20) - 10;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  const lastX = (telemetryHistory.length - 1) * stepX;
  const lastY = h - ((telemetryHistory[telemetryHistory.length - 1].val - min) / (max - min)) * (h - 20) - 10;
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
  ctx.fillStyle = "#10f17f";
  ctx.fill();
}
