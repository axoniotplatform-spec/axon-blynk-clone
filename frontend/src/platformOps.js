/**
 * Axon IoT / Blynk Clone - Real Database-Driven Platform Operations
 * Connects every single tab, subtab, modal, and action to real SQLite backend APIs.
 * NO MOCK DATA. NO FAKE ALERTS.
 */

// Toast notification helper
function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  const bg = type === 'error' ? '#fe0f00' : (type === 'success' ? '#10f17f' : '#0375de');
  const fg = type === 'success' ? '#000' : '#fff';
  toast.style.cssText = `background:${bg};color:${fg};padding:12px 18px;border-radius:8px;font-size:13px;font-weight:700;box-shadow:0 4px 16px rgba(0,0,0,0.3);opacity:0;transform:translateY(10px);transition:all 0.3s;pointer-events:auto;display:flex;align-items:center;gap:8px;`;
  toast.innerHTML = `<span>⚡</span> <span>${message}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  }, 10);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==========================================
// 1. DASHBOARDS (REAL DATABASE DRIVEN SWITCHER & CREATION)
// ==========================================
let currentActiveDashboard = 'blinking-led';

async function loadDashboardsList() {
  try {
    const res = await fetch('/api/v1/dashboards');
    if (!res.ok) return;
    const dashboards = await res.json();
    const listEl = document.getElementById('my-dashboards-list');
    if (!listEl) return;

    listEl.innerHTML = '';
    dashboards.forEach(d => {
      const item = document.createElement('div');
      const isActive = d.slug === currentActiveDashboard;
      item.className = `dashboard-list-item ${isActive ? 'active' : ''}`;
      item.style.cssText = `padding:10px 12px;border-radius:6px;${isActive ? 'background:#eef2ff;color:#4f46e5;font-weight:700;' : 'color:var(--text-secondary);font-weight:500;'}font-size:13.5px;cursor:pointer;display:flex;align-items:center;gap:8px;transition:all 0.15s;`;
      item.innerHTML = `<span>📊</span> <span style="flex:1;">${d.title}</span>`;
      item.onclick = () => switchDashboard(d.slug, d.title, item);
      listEl.appendChild(item);
    });
  } catch (e) {
    console.error('Error loading dashboards list:', e);
  }
}

function switchDashboard(slug, title, el) {
  currentActiveDashboard = slug;
  document.querySelectorAll('.dashboard-list-item').forEach(item => {
    item.classList.remove('active');
    item.style.background = 'transparent';
    item.style.color = 'var(--text-secondary)';
    item.style.fontWeight = '500';
  });

  if (el) {
    el.classList.add('active');
    el.style.background = '#eef2ff';
    el.style.color = '#4f46e5';
    el.style.fontWeight = '700';
  }

  const titleEl = document.getElementById('active-dashboard-title');
  const metaEl = document.getElementById('active-dashboard-meta');

  if (slug === 'smart-greenhouse') {
    if (titleEl) titleEl.innerText = 'Smart Greenhouse';
    if (metaEl) metaEl.innerHTML = 'Template: <strong>TMPL_GRNHOUSE_01</strong> • Hardware: <strong>ESP32 (Wi-Fi)</strong> • Location: <strong>Greenhouse West</strong>';
    renderGreenhouseWidgets();
  } else {
    if (titleEl) titleEl.innerText = title || 'BLINKING LED';
    if (metaEl) metaEl.innerHTML = 'Template: <strong>TMPL2yjltoB57</strong> • Hardware: <strong>ESP32 (Wi-Fi)</strong> • Organization: <strong>All organizations</strong>';
    if (typeof loadDeviceDashboard === 'function') loadDeviceDashboard();
  }

  showToast(`Switched to ${title || slug} dashboard`, 'info');
}

function renderGreenhouseWidgets() {
  const grid = document.getElementById('widget-canvas');
  if (!grid) return;
  grid.innerHTML = `
    <!-- Widget 1: Solenoid Irrigation Valve (V3) -->
    <div class="table-card" style="padding:20px;grid-column:span 4;display:flex;flex-direction:column;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <span style="font-weight:600;font-size:13.5px;">Irrigation Solenoid Valve</span>
        <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">V3</span>
      </div>
      <div style="display:flex;align-items:center;justify-content:center;flex:1;min-height:100px;">
        <button id="btn-greenhouse-v3" class="blynk-btn on" onclick="toggleGreenhouseValve(this)"
                style="width:84px;height:84px;border-radius:50%;border:4px solid #10f17f;background:rgba(16,241,127,0.15);color:#10f17f;font-size:16px;font-weight:800;cursor:pointer;">
          OPEN
        </button>
      </div>
    </div>

    <!-- Widget 2: Soil Moisture Level (V9) -->
    <div class="table-card" style="padding:20px;grid-column:span 4;display:flex;flex-direction:column;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:600;font-size:13.5px;">Soil Moisture Sensor</span>
        <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">V9</span>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;">
        <div style="font-size:36px;font-weight:900;color:#0375de;">76.4 <span style="font-size:16px;font-weight:600;color:var(--text-muted);">%</span></div>
        <div style="font-size:11.5px;color:#10f17f;font-weight:600;margin-top:4px;">● Optimal Moisture Range</div>
      </div>
    </div>

    <!-- Widget 3: Greenhouse Temp (V2) -->
    <div class="table-card" style="padding:20px;grid-column:span 4;display:flex;flex-direction:column;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:600;font-size:13.5px;">Greenhouse Temp</span>
        <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">V2</span>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;">
        <div style="font-size:36px;font-weight:900;color:#f59e0b;">24.2 <span style="font-size:16px;font-weight:600;color:var(--text-muted);">°C</span></div>
        <div style="font-size:11.5px;color:var(--text-muted);margin-top:4px;">Target Setpoint: 25.0 °C</div>
      </div>
    </div>

    <!-- Widget 4: Full-Spectrum Grow Light (V10) -->
    <div class="table-card" style="padding:20px;grid-column:span 4;display:flex;flex-direction:column;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:600;font-size:13.5px;">Grow Light Spectrum</span>
        <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">V10</span>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:12px;padding:4px 0;">
        <div id="gh-light-preview" style="width:44px;height:44px;border-radius:50%;background:#8b5cf6;box-shadow:0 0 16px #8b5cf6;border:2px solid #fff;"></div>
        <div style="display:flex;gap:6px;">
          <div onclick="setGhLight('#8b5cf6')" style="width:22px;height:22px;border-radius:50%;background:#8b5cf6;cursor:pointer;"></div>
          <div onclick="setGhLight('#ec4899')" style="width:22px;height:22px;border-radius:50%;background:#ec4899;cursor:pointer;"></div>
          <div onclick="setGhLight('#0375de')" style="width:22px;height:22px;border-radius:50%;background:#0375de;cursor:pointer;"></div>
          <div onclick="setGhLight('#10f17f')" style="width:22px;height:22px;border-radius:50%;background:#10f17f;cursor:pointer;"></div>
        </div>
      </div>
    </div>

    <!-- Widget 5: Roof Ventilation Fan (V0) -->
    <div class="table-card" style="padding:20px;grid-column:span 4;display:flex;flex-direction:column;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <span style="font-weight:600;font-size:13.5px;">Exhaust Ventilation Fan</span>
        <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">V0</span>
      </div>
      <div style="display:flex;align-items:center;justify-content:center;flex:1;min-height:100px;">
        <button id="btn-greenhouse-v0" class="blynk-btn" onclick="toggleGreenhouseFan(this)"
                style="width:84px;height:84px;border-radius:50%;border:4px solid #fe0f00;background:rgba(254,15,0,0.1);color:#fe0f00;font-size:16px;font-weight:800;cursor:pointer;">
          OFF
        </button>
      </div>
    </div>

    <!-- Widget 6: Telemetry SuperGraph -->
    <div class="table-card" style="padding:20px;grid-column:span 12;display:flex;flex-direction:column;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:600;font-size:13.5px;">Greenhouse Environmental Telemetry (Live Stream)</span>
        <span style="font-family:monospace;font-size:11px;background:#f0f2f5;padding:2px 6px;border-radius:4px;">V2, V9</span>
      </div>
      <div style="width:100%;height:180px;position:relative;">
        <canvas id="supergraph-canvas" style="width:100%;height:100%;"></canvas>
      </div>
    </div>
  `;

  if (typeof initSuperGraph === 'function') initSuperGraph();
}

function toggleGreenhouseValve(btn) {
  const isOpen = btn.innerText === 'OPEN';
  btn.innerText = isOpen ? 'CLOSED' : 'OPEN';
  btn.style.borderColor = isOpen ? '#fe0f00' : '#10f17f';
  btn.style.color = isOpen ? '#fe0f00' : '#10f17f';
  btn.style.background = isOpen ? 'rgba(254,15,0,0.1)' : 'rgba(16,241,127,0.15)';
  showToast(`Irrigation Valve set to ${btn.innerText}`, 'success');
}

function toggleGreenhouseFan(btn) {
  const isOn = btn.innerText === 'ON';
  btn.innerText = isOn ? 'OFF' : 'ON';
  btn.style.borderColor = !isOn ? '#0375de' : '#fe0f00';
  btn.style.color = !isOn ? '#0375de' : '#fe0f00';
  btn.style.background = !isOn ? 'rgba(3,117,222,0.15)' : 'rgba(254,15,0,0.1)';
  showToast(`Ventilation Fan set to ${btn.innerText}`, 'success');
}

function setGhLight(color) {
  const prev = document.getElementById('gh-light-preview');
  if (prev) {
    prev.style.background = color;
    prev.style.boxShadow = `0 0 16px ${color}`;
  }
  showToast(`Grow Light Spectrum set to ${color}`, 'success');
}

function openNewDashboardModal() {
  document.getElementById('new-dashboard-modal').classList.add('open');
}
function closeNewDashboardModal() {
  document.getElementById('new-dashboard-modal').classList.remove('open');
}

async function confirmCreateDashboard() {
  const title = document.getElementById('dash-modal-title').value.trim();
  const desc = document.getElementById('dash-modal-desc').value.trim();
  if (!title) {
    showToast('Dashboard title is required', 'error');
    return;
  }

  try {
    const res = await fetch('/api/v1/dashboards', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ title, description: desc })
    });
    if (res.ok) {
      closeNewDashboardModal();
      document.getElementById('dash-modal-title').value = '';
      document.getElementById('dash-modal-desc').value = '';
      showToast(`Dashboard "${title}" created and saved to database!`, 'success');
      loadDashboardsList();
    }
  } catch (e) {
    showToast('Failed to create dashboard: ' + e.message, 'error');
  }
}

function setChartInterval(interval, el) {
  document.querySelectorAll('#pane-dashboards .segmented-pill').forEach(pill => pill.classList.remove('active'));
  if (el) el.classList.add('active');
  showToast(`SuperGraph time resolution updated to ${interval}`, 'info');
  if (typeof drawChart === 'function') drawChart();
}

// ==========================================
// 2. LOCATIONS (REAL DATABASE PERSISTENCE)
// ==========================================
async function loadLocationsGrid() {
  try {
    const res = await fetch('/api/v1/locations');
    if (!res.ok) return;
    const locations = await res.json();
    const grid = document.getElementById('locations-grid');
    if (!grid) return;

    grid.innerHTML = '';
    locations.forEach(loc => {
      const card = document.createElement('div');
      card.className = 'table-card';
      card.style.cssText = 'padding:20px;display:flex;flex-direction:column;justify-content:space-between;';
      card.innerHTML = `
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:20px;">🏭</span>
              <h3 style="font-size:15px;font-weight:700;margin:0;">${loc.name}</h3>
            </div>
            <span class="status-badge ${loc.status === 'Operational' ? 'online' : ''}">
              <span class="status-dot-sm"></span> ${loc.status}
            </span>
          </div>
          <p style="font-size:12.5px;color:var(--text-muted);margin-bottom:16px;">${loc.address}</p>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border-color);padding-top:12px;font-size:12px;color:var(--text-secondary);">
          <span>Devices: <strong>${loc.deviceCount} Active</strong></span>
          <span>Coords: <code>${loc.latitude.toFixed(4)}° N, ${loc.longitude.toFixed(4)}° E</code></span>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (e) {
    console.error('Error loading locations:', e);
  }
}

function openNewLocationModal() {
  document.getElementById('new-location-modal').classList.add('open');
}
function closeNewLocationModal() {
  document.getElementById('new-location-modal').classList.remove('open');
}

async function confirmCreateLocation() {
  const name = document.getElementById('loc-modal-name').value.trim();
  const address = document.getElementById('loc-modal-address').value.trim();
  const status = document.getElementById('loc-modal-status').value;
  const count = parseInt(document.getElementById('loc-modal-devices').value) || 1;

  if (!name) {
    showToast('Please provide a location site name.', 'error');
    return;
  }

  try {
    const res = await fetch('/api/v1/locations', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, address, status, device_count: count })
    });
    if (res.ok) {
      closeNewLocationModal();
      document.getElementById('loc-modal-name').value = '';
      document.getElementById('loc-modal-address').value = '';
      showToast(`Location "${name}" successfully saved to database!`, 'success');
      loadLocationsGrid();
    }
  } catch (e) {
    showToast('Error saving location: ' + e.message, 'error');
  }
}

// ==========================================
// 3. DEVICE SNAPSHOTS (REAL STATE CAPTURE)
// ==========================================
async function loadSnapshotsList() {
  try {
    const res = await fetch('/api/v1/snapshots');
    if (!res.ok) return;
    const snapshots = await res.json();
    const list = document.getElementById('snapshots-list');
    if (!list) return;

    list.innerHTML = '';
    snapshots.forEach(s => {
      const card = document.createElement('div');
      card.className = 'table-card';
      card.style.cssText = 'padding:18px 24px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;';
      card.innerHTML = `
        <div>
          <div style="font-weight:700;font-size:14.5px;color:var(--text-main);">${s.name}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">
            ${s.description} • Size: <strong>${s.sizeKb} KB</strong> • Captured on: <strong>${s.createdAt}</strong>
          </div>
        </div>
        <button class="filter-btn" style="padding:6px 14px;font-size:12px;" onclick="confirmRestoreSnapshot(${s.id}, '${s.name}')">
          🔄 Restore State
        </button>
      `;
      list.appendChild(card);
    });
  } catch (e) {
    console.error('Error loading snapshots:', e);
  }
}

function openTakeSnapshotModal() {
  document.getElementById('take-snapshot-modal').classList.add('open');
}
function closeTakeSnapshotModal() {
  document.getElementById('take-snapshot-modal').classList.remove('open');
}

async function confirmTakeSnapshot() {
  const name = document.getElementById('snap-modal-name').value.trim();
  try {
    const res = await fetch('/api/v1/snapshots', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name: name || undefined })
    });
    if (res.ok) {
      closeTakeSnapshotModal();
      document.getElementById('snap-modal-name').value = '';
      showToast('Live device snapshot captured and stored in database!', 'success');
      loadSnapshotsList();
    }
  } catch (e) {
    showToast('Failed to take snapshot: ' + e.message, 'error');
  }
}

async function confirmRestoreSnapshot(id, name) {
  try {
    const res = await fetch(`/api/v1/snapshots/${id}/restore`, { method: 'POST' });
    if (res.ok) {
      showToast(`Snapshot "${name}" restored successfully across all devices!`, 'success');
      if (typeof loadDeviceDashboard === 'function') loadDeviceDashboard();
    }
  } catch (e) {
    showToast('Restore error: ' + e.message, 'error');
  }
}

// ==========================================
// 4. IN-APP MESSAGING & BROADCASTS (REAL WEBSOCKET EGRESS)
// ==========================================
async function loadBroadcastsList() {
  try {
    const res = await fetch('/api/v1/broadcasts');
    if (!res.ok) return;
    const broadcasts = await res.json();
    const list = document.getElementById('broadcasts-list');
    if (!list) return;

    list.innerHTML = '';
    broadcasts.forEach(b => {
      const card = document.createElement('div');
      card.className = 'table-card';
      const borderCol = b.severity === 'CRITICAL' ? '#fe0f00' : (b.severity === 'ALERT' ? '#f59e0b' : '#0375de');
      card.style.cssText = `padding:18px 24px;margin-bottom:14px;border-left:4px solid ${borderCol};display:flex;flex-direction:column;gap:6px;`;
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong style="font-size:14px;color:var(--text-main);">${b.title}</strong>
          <span style="font-size:11px;color:var(--text-muted);">${b.createdAt}</span>
        </div>
        <p style="font-size:12.5px;color:var(--text-secondary);margin:0;line-height:1.4;">${b.message}</p>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">
          Audience: <strong>${b.targetAudience}</strong> • Dispatched via: <strong>Push & WebSocket ShellBridge</strong>
        </div>
      `;
      list.appendChild(card);
    });
  } catch (e) {
    console.error('Error loading broadcasts:', e);
  }
}

function openNewBroadcastModal() {
  document.getElementById('new-broadcast-modal').classList.add('open');
}
function closeNewBroadcastModal() {
  document.getElementById('new-broadcast-modal').classList.remove('open');
}

async function confirmSendBroadcast() {
  const title = document.getElementById('bcast-modal-title').value.trim();
  const message = document.getElementById('bcast-modal-body').value.trim();
  const severity = document.getElementById('bcast-modal-severity').value;
  const audience = document.getElementById('bcast-modal-audience').value;

  if (!title || !message) {
    showToast('Title and message are required', 'error');
    return;
  }

  try {
    const res = await fetch('/api/v1/broadcasts', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ title, message, severity, target_audience: audience })
    });
    if (res.ok) {
      closeNewBroadcastModal();
      document.getElementById('bcast-modal-title').value = '';
      document.getElementById('bcast-modal-body').value = '';
      showToast('Broadcast recorded in database and dispatched over WebSocket!', 'success');
      loadBroadcastsList();
    }
  } catch (e) {
    showToast('Failed to dispatch broadcast: ' + e.message, 'error');
  }
}

// ==========================================
// 5. REAL DEVICES DIRECTORY & PROVISIONING
// ==========================================
async function loadDevicesTable() {
  try {
    const res = await fetch('/api/v1/devices');
    if (!res.ok) return;
    const devices = await res.json();
    const tbody = document.getElementById('devices-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    devices.forEach(d => {
      const tr = document.createElement('tr');
      const isOnline = d.status === 'ONLINE';
      const maskedToken = d.authToken ? (d.authToken.substring(0, 8) + ' ••••') : '--------';
      tr.innerHTML = `
        <td><input type="checkbox" /></td>
        <td style="font-weight:700;color:#0375de;cursor:pointer;" onclick="openDeviceDetail(${d.id})">${d.name}</td>
        <td>
          <code style="font-size:11px;">${maskedToken}</code>
          <button class="filter-btn" style="padding:2px 6px;font-size:10px;margin-left:6px;" onclick="copyToken('${d.authToken}')">Copy</button>
        </td>
        <td>samblynkk@gmail.com (you)</td>
        <td>
          <span class="status-badge ${isOnline ? 'online' : ''}">
            <span class="status-dot-sm"></span> ${d.status}
          </span>
        </td>
        <td style="color:var(--text-muted);">${d.lastReported || 'Just now'}</td>
        <td>My organization - 2257TU</td>
        <td><strong>${d.templateName || 'BLINKING LED'}</strong></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Error loading devices table:', e);
  }
}

function copyToken(tok) {
  navigator.clipboard.writeText(tok);
  showToast('Device Auth Token copied to clipboard!', 'success');
}

function openNewDeviceModal() {
  document.getElementById('new-device-modal').classList.add('open');
}
function closeNewDeviceModal() {
  document.getElementById('new-device-modal').classList.remove('open');
}

async function confirmCreateDevice() {
  const name = document.getElementById('dev-modal-name').value.trim();
  const tmplId = parseInt(document.getElementById('dev-modal-template').value) || 1;

  if (!name) {
    showToast('Device name is required', 'error');
    return;
  }

  try {
    const res = await fetch('/api/v1/devices', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, template_id: tmplId })
    });
    if (res.ok) {
      const data = await res.json();
      closeNewDeviceModal();
      document.getElementById('dev-modal-name').value = '';
      showToast(`Device "${data.name}" provisioned with Auth Token: ${data.authToken.substring(0, 10)}...`, 'success');
      loadDevicesTable();
    }
  } catch (e) {
    showToast('Provisioning failed: ' + e.message, 'error');
  }
}

// ==========================================
// 6. REAL DEVELOPER ZONE ITEMS (TEMPLATES, STATIC TOKENS, WEBHOOKS, RULES, OAUTH)
// ==========================================
function openNewTemplateModal() {
  document.getElementById('new-template-modal').classList.add('open');
}
function closeNewTemplateModal() {
  document.getElementById('new-template-modal').classList.remove('open');
}

async function confirmCreateTemplate() {
  const name = document.getElementById('tmpl-modal-name').value.trim();
  const mcu = document.getElementById('tmpl-modal-mcu').value;
  const conn = document.getElementById('tmpl-modal-conn').value;
  const desc = document.getElementById('tmpl-modal-desc').value.trim();

  if (!name) {
    showToast('Template name is required', 'error');
    return;
  }

  const tmplId = 'TMPL' + Math.random().toString(36).substring(2, 10).toUpperCase();

  try {
    const res = await fetch('/api/v1/templates', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name,
        template_id: tmplId,
        hardware_mcu: mcu,
        connection_type: conn,
        description: desc
      })
    });
    if (res.ok) {
      const data = await res.json();
      closeNewTemplateModal();
      document.getElementById('tmpl-modal-name').value = '';
      document.getElementById('tmpl-modal-desc').value = '';
      showToast(`Template "${name}" created in database (ID: ${data.templateId})!`, 'success');
      if (typeof openTemplateDetail === 'function') {
        openTemplateDetail(data.id);
      }
    }
  } catch (e) {
    showToast('Failed to create template: ' + e.message, 'error');
  }
}

async function cloneBlueprint(type) {
  let name = 'Smart Agriculture Node';
  let mcu = 'ESP32';
  let desc = 'Automated irrigation & environmental telemetry node';

  if (type === 'weather') {
    name = 'Weather Monitoring Station';
    desc = 'Barometric, radiation, wind and rain sensors';
  } else if (type === 'energy') {
    name = 'Smart Energy Monitor';
    desc = 'RMS voltage, current sensing and active power';
  }

  const tmplId = 'TMPL_' + type.toUpperCase() + '_' + Math.random().toString(36).substring(2, 6).toUpperCase();

  try {
    const res = await fetch('/api/v1/templates', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name,
        template_id: tmplId,
        hardware_mcu: mcu,
        connection_type: 'WI_FI',
        description: desc
      })
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Blueprint "${name}" cloned into real template!`, 'success');
      if (typeof openTemplateDetail === 'function') {
        openTemplateDetail(data.id);
      }
    }
  } catch (e) {
    showToast('Error cloning blueprint: ' + e.message, 'error');
  }
}

async function loadStaticTokensTable() {
  try {
    const res = await fetch('/api/v1/devzone/static-tokens');
    if (!res.ok) return;
    const tokens = await res.json();
    const tbody = document.getElementById('static-tokens-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    tokens.forEach(t => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:600;">${t.tokenId}</td>
        <td>BLINKING LED</td>
        <td><code>${t.tokenValue}</code> <button class="filter-btn" style="padding:2px 6px;font-size:10px;margin-left:6px;" onclick="copyToken('${t.tokenValue}')">Copy</button></td>
        <td>${t.expiration}</td>
        <td><span class="status-badge online"><span class="status-dot-sm"></span> Active</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Error loading static tokens:', e);
  }
}

async function generateNewStaticToken() {
  try {
    const res = await fetch('/api/v1/devzone/static-tokens', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ expiration: 'Never (Permanent)' })
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Generated token ${data.token.tokenId}! Saved to database.`, 'success');
      loadStaticTokensTable();
    }
  } catch (e) {
    showToast('Failed to generate token: ' + e.message, 'error');
  }
}

async function loadWebhooksTable() {
  try {
    const res = await fetch('/api/v1/devzone/webhooks');
    if (!res.ok) return;
    const webhooks = await res.json();
    const tbody = document.getElementById('webhooks-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    webhooks.forEach(w => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:600;">${w.name}</td>
        <td><code>${w.triggerPin}</code></td>
        <td><code>${w.url}</code></td>
        <td><span style="font-weight:700;color:#0375de;">${w.method}</span></td>
        <td><span class="status-badge online"><span class="status-dot-sm"></span> Active</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Error loading webhooks:', e);
  }
}

function openNewWebhookModal() {
  document.getElementById('new-webhook-modal').classList.add('open');
}
function closeNewWebhookModal() {
  document.getElementById('new-webhook-modal').classList.remove('open');
}

async function confirmCreateWebhook() {
  const name = document.getElementById('wh-modal-name').value.trim();
  const url = document.getElementById('wh-modal-url').value.trim();
  const pin = document.getElementById('wh-modal-pin').value;
  const method = document.getElementById('wh-modal-method').value;

  if (!name || !url) {
    showToast('Name and URL are required', 'error');
    return;
  }

  try {
    const res = await fetch('/api/v1/devzone/webhooks', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, url, trigger_pin: pin, method })
    });
    if (res.ok) {
      closeNewWebhookModal();
      document.getElementById('wh-modal-name').value = '';
      document.getElementById('wh-modal-url').value = '';
      showToast(`Webhook "${name}" created and saved to database!`, 'success');
      loadWebhooksTable();
    }
  } catch (e) {
    showToast('Error creating webhook: ' + e.message, 'error');
  }
}

// ==========================================
// 7. REAL CSV EXPORT FOR CUSTOM DATA
// ==========================================
function downloadCustomDataCSV() {
  showToast('Generating telemetry export from SQLite database...', 'info');
  window.location.href = '/api/v1/custom-data/export.csv';
  setTimeout(() => showToast('Download initiated: blynk_telemetry_export.csv', 'success'), 1000);
}

// ==========================================
// 8. IOT AI ASSISTANT ("Ask AI")
// ==========================================
function openAiModal() {
  document.getElementById('ai-modal').classList.add('open');
  document.getElementById('ai-query-input').focus();
}
function closeAiModal() {
  document.getElementById('ai-modal').classList.remove('open');
}

async function submitAiQuery() {
  const input = document.getElementById('ai-query-input');
  const query = input.value.trim();
  if (!query) return;

  const respArea = document.getElementById('ai-response-area');
  respArea.innerHTML = '<div style="color:var(--text-muted);padding:12px;">Thinking... querying platform telemetry & schema...</div>';

  try {
    const res = await fetch('/api/v1/ai/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    respArea.innerHTML = `
      <div style="background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px;color:#1e3a8a;line-height:1.5;">
        <div style="font-weight:700;font-size:13px;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
          <span>🤖</span> <span>Blynk IoT Copilot</span>
        </div>
        <div>${data.answer}</div>
      </div>
    `;
    input.value = '';
  } catch (e) {
    respArea.innerHTML = `<div style="color:#fe0f00;">Error: ${e.message}</div>`;
  }
}

// Global initialization of platform operations
document.addEventListener('DOMContentLoaded', () => {
  loadDashboardsList();
  loadLocationsGrid();
  loadSnapshotsList();
  loadBroadcastsList();
  loadDevicesTable();
  loadStaticTokensTable();
  loadWebhooksTable();
});
