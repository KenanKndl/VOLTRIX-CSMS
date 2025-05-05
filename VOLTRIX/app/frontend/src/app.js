// ========================================================
// 🔧 CONFIG & GLOBALS
// ========================================================
const API = "http://localhost:8000";
const chargingSessions = new Map();
let visibleChargingEvseIndex = null;

const ocppStatuses = [
  "Available",
  "Occupied",
  "Reserved",
  "Unavailable",
  "Faulted"
];

const labelMap = {
  "Available": "🟢 Available",
  "Occupied": "🔵 Occupied",
  "Reserved": "🟡 Reserved",
  "Unavailable": "⚪ Unavailable",
  "Faulted": "❌ Faulted"
};



// ========================================================
// 🔋 MODAL CONTROL FUNCTIONS
// ========================================================
function showChargingModal(index, session = null) {
  const modal = document.getElementById("charging-modal");
  modal.classList.remove("hidden");
  modal.dataset.index = index;
  visibleChargingEvseIndex = index;
  const data = session || chargingSessions.get(index);
  if (!data) return;
  updateChargingModal(data);
}

function hideChargingModal() {
  const modal = document.getElementById("charging-modal");
  modal.classList.add("hidden");
  modal.removeAttribute("data-index");
}

function updateChargingModal({ ev, evse, progress, totalSec }) {
  const percent = Math.min((progress / totalSec) * 100, 100);
  const remaining = totalSec - progress;
  const energyDelivered = (ev.battery_capacity_kWh * (percent / 100)).toFixed(2);

  document.getElementById("charging-ev-name").textContent = `${ev.brand} ${ev.model} (${ev.id})`;
  document.getElementById("charging-evse-name").textContent = `${evse.name}`;
  document.getElementById("charging-remaining-time").textContent = `Estimated Time: ${totalSec} sec`;
  document.getElementById("charging-percentage").textContent = `${Math.round(percent)}%`;
  document.getElementById("charging-energy-info").textContent = `${energyDelivered} kWh`;
  document.getElementById("charging-eta").textContent = `Time Left: ${remaining} sec`;

  document.getElementById("battery-fill").style.height = `${percent}%`;
}

// ========================================================
// 🧾 FORM VE PANEL AÇ / KAPAT
// ========================================================
document.getElementById("add-evse-btn").onclick = () =>
  document.getElementById("evse-form").style.display = "block";

document.getElementById("cancel-evse-btn").onclick = () => {
  const form = document.getElementById("evse-form");
  form.reset();
  form.style.display = "none";
};

// Admin Paneli açarken overlay'i göster
document.getElementById("admin-page-btn").onclick = () => {
  document.getElementById("admin-panel").classList.add("open");
  document.getElementById("admin-panel-overlay").style.display = "block";
};

// Admin Paneli kapatırken overlay'i gizle
document.getElementById("close-admin-panel").onclick = () => {
  document.getElementById("admin-panel").classList.remove("open");
  document.getElementById("admin-panel-overlay").style.display = "none";
};


// ========================================================
// 📥 EVSE EKLEME FORMU GÖNDER
// ========================================================
document.getElementById("evse-form").onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = {
    name: form.name.value,
    brand: form.brand.value,
    model: form.model.value,
    vendor: form.vendor.value,
    latitude: parseFloat(form.latitude.value),
    longitude: parseFloat(form.longitude.value),
    status: form.status.value
  };

  await fetch(`${API}/evses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });

  form.reset();
  form.style.display = "none";
  await loadEvseList();
  await loadDashboard();
};

// ========================================================
// 🧠 STATUS DROPDOWN YÜKLE
// ========================================================
function loadStatuses() {
  const select = document.getElementById("status-select");
  select.innerHTML = "<option value=''>Select Status</option>";

  ocppStatuses.forEach(status => {
    const option = document.createElement("option");
    option.value = status;
    option.textContent = labelMap[status] || status;
    select.appendChild(option);
  });
}


// ========================================================
// 📊 DASHBOARD VERİSİ
// ========================================================
async function loadDashboard() {
  const res = await fetch(`${API}/evses/summary`);
  const data = await res.json();
  document.getElementById("total-evse").textContent = data.total;
  document.getElementById("connected-evse").textContent = data.connected;
}

// ========================================================
// 📋 EVSE LİSTELEME VE KARTLAR
// ========================================================
async function loadEvseList() {
  const res = await fetch(`${API}/evses`);
  const evses = await res.json();
  const list = document.getElementById("evse-list-content");
  const idleEvseSelect = document.getElementById("idle-evse-select");

  list.innerHTML = "";
  idleEvseSelect.innerHTML = "<option value=''>Select Idle EVSE</option>";

  evses.forEach((evse, index) => {
    const card = document.createElement("div");
    card.className = "evse-card";

    const isDisconnected = evse.status === "Unavailable" || evse.status === "Faulted";
    const buttonClass = isDisconnected ? "evse-connect-btn" : "evse-disconnect-btn";
    const buttonLabel = isDisconnected ? "🔌 Connect" : "🔌 Disconnect";
    const statusClass = evse.status.toLowerCase();

    let extraButton = "";
    if (evse.status === "Reserved") {
      extraButton = `
        <button class="evse-plug-btn" onclick="plugEvse(${index})">🔌 Plug</button>
      `;
    } else if (evse.status === "Occupied") {
      extraButton = `
        <button class="evse-start-btn" onclick="startCharging(${index})">⚡ Start Charging</button>
      `;
    }
    
    card.innerHTML = `
      <div class="evse-actions-box">
        <button class="${buttonClass}" onclick="toggleConnection(${index})">${buttonLabel}</button>
        ${extraButton}
        <button class="evse-delete-btn" onclick="deleteEvse(${index})">🗑️ Delete</button>
      </div>
      <div class="evse-title">🔋 ${evse.name} (${evse.model})</div>
      <div class="evse-meta">🏽 Brand: ${evse.brand} | 🏪 Vendor: ${evse.vendor}</div>
      <div class="evse-meta">📍 ${evse.latitude}, ${evse.longitude}</div>
      <div class="evse-meta">⚡ Max Power: ${evse.max_power_kW} kW</div>
      <span class="evse-status status-${statusClass}">${labelMap[evse.status] || evse.status}</span>
    `;

    list.appendChild(card);

    if (evse.status === "Available") {
      const opt = document.createElement("option");
      opt.value = index;
      opt.textContent = `${evse.name} (${evse.model})`;
      idleEvseSelect.appendChild(opt);
    }
  });
}

// ========================================================
// 🔌 BAĞLANTI DURUMU DEĞİŞTİR
// ========================================================
async function toggleConnection(index) {
  const evses = await (await fetch(`${API}/evses`)).json();
  const evse = evses[index];

  if (evse.status === "Unavailable" || evse.status === "Faulted") {
    const res = await fetch(`${API}/evses/${index}/connect`, {
      method: "POST"
    });

    const result = await res.json();
    if (!res.ok) {
      alert(`❌ Connect failed: ${result.detail || "Unknown error"}`);
      return;
    }

    alert("✅ EVSE connected.");
  } else {
    const res = await fetch(`${API}/evses/${index}/disconnect`, {
      method: "POST"
    });

    const result = await res.json();
    if (!res.ok) {
      alert(`❌ Disconnect failed: ${result.detail || "Unknown error"}`);
      return;
    }

    alert("🔌 EVSE disconnected.");
  }

  await loadEvseList();
  await loadDashboard();
}


async function plugEvse(index) {
  const evses = await (await fetch(`${API}/evses`)).json();
  const evse = evses[index];

  if (evse.status !== "Reserved") {
    return alert("❌ EVSE is not reserved.");
  }

  try {
    const res = await fetch(`${API}/evses/${index}/plug`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    const result = await res.json();

    if (res.ok && result.status === "occupied") {
      console.log("✅ Plug successful, updating UI.");
    } else {
      alert(`❌ Plug failed: ${result.message || "Unknown error"}`);
    }

  } catch (err) {
    console.error("❌ Plug API error:", err);
    alert("❌ Plug failed due to network error.");
  }

  // Refresh UI to show updated EVSE state
  await loadEvseList();
  await loadDashboard();
}

// ========================================================
// ⚡ ŞARJ BAŞLAT
// ========================================================
async function startCharging(index) {
  const evses = await (await fetch(`${API}/evses`)).json();
  const evse = evses[index];
  const evs = await (await fetch(`${API}/evs`)).json();
  const ev = evs.find(e => e.connected_evse_id === evse.name);
  if (!ev) return alert("❌ No EV reserved for this EVSE.");

  // 🚀 Sadece başlatma çağrısı
  const startRes = await fetch(`${API}/evses/${index}/start`, {
    method: "POST"
  });

  if (!startRes.ok) {
    const result = await startRes.json();
    return alert(`❌ Start failed: ${result.detail || "Unknown error"}`);
  }

  const totalSec = 60;
  let progress = 0;

  const btn = document.querySelector(`.evse-start-btn[onclick="startCharging(${index})"]`);
  if (btn) {
    btn.textContent = "🔍 Details";
    btn.onclick = () => showChargingModal(index);
  }

  if (visibleChargingEvseIndex === null || visibleChargingEvseIndex === index) {
    visibleChargingEvseIndex = index;
    showChargingModal(index, { ev, evse, progress, totalSec });
  }

  const interval = setInterval(async () => {
    progress++;
    const percent = Math.min((progress / totalSec) * 100, 100);

    if (visibleChargingEvseIndex === index) {
      updateChargingModal({ ev, evse, progress, totalSec });
    }

    const newSoc = ev.current_soc + ((ev.target_soc - ev.current_soc) * (progress / totalSec));
    await fetch(`${API}/evs/${ev.id}/soc`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_soc: newSoc })
    });

    if (progress >= totalSec) {
      clearInterval(chargingSessions.get(index).interval);

      // ⚡ Şarj bitince durdurma çağrısı
      await fetch(`${API}/evses/${index}/stop`, { method: "POST" });

      chargingSessions.delete(index);
      if (visibleChargingEvseIndex === index) {
        setTimeout(() => {
          hideChargingModal();
          visibleChargingEvseIndex = null;
        }, 2000);
      }

      await loadDashboard();
      await loadEvseList();
    }
  }, 1000);

  chargingSessions.set(index, { interval, ev, evse, progress, totalSec });
}




async function disconnectEvse(index) {
  await fetch(`${API}/evses/${index}/disconnect`, {
    method: "POST"
  });

  await loadEvseList();
  await loadDashboard();
}


// ========================================================
// 📌 REZERVASYON PANELİ
// ========================================================
const vehicles = [
  { id: "EV-001", brand: "Tesla", model: "Model 3" },
  { id: "EV-002", brand: "Renault", model: "ZOE" },
  { id: "EV-003", brand: "Hyundai", model: "Kona" }
];

function populateVehicleDropdown() {
  const select = document.getElementById("ev-select");
  select.innerHTML = "<option value=''>Select Vehicle</option>";
  vehicles.forEach(v => {
    const opt = document.createElement("option");
    opt.value = v.id;
    opt.textContent = `${v.brand} ${v.model} (${v.id})`;
    select.appendChild(opt);
  });
}

async function updateReservationInfo() {
  const evId = document.getElementById("ev-select").value;
  const evseIndex = document.getElementById("idle-evse-select").value;
  const box = document.getElementById("reservation-feedback");
  const button = document.getElementById("assign-reservation");

  if (!evId || evseIndex === "") {
    box.className = "reservation-box error";
    box.innerHTML = `⚠️ Select both vehicle and EVSE`;
    box.classList.remove("hidden");
    button.disabled = true;
    return;
  }

  const res = await fetch(`${API}/reservation/estimate?ev_id=${evId}&evse_index=${evseIndex}`);
  const result = await res.json();

  if (result.reservable) {
    box.className = "reservation-box success";
    box.innerHTML = `✅ Ready to reserve – ⏱️ ${result.estimated_time_min} min`;
    button.disabled = false;
  } else {
    box.className = "reservation-box error";
    box.innerHTML = `❌ ${result.reason || "Unavailable"}`;
    button.disabled = true;
  }

  box.classList.remove("hidden");
}

document.getElementById("assign-reservation").onclick = async () => {
  const evId = document.getElementById("ev-select").value;
  const evseIndex = document.getElementById("idle-evse-select").value;

  const res = await fetch(`${API}/ocpp/reserve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ev_id: evId, evse_index: parseInt(evseIndex) })
  });

  const result = await res.json();

  if (result.status === "Accepted") {
    alert("✅ EVSE başarıyla rezerve edildi.");
    await loadEvseList();
    await loadDashboard();
    await populateIdleEvseDropdown();
  } else {
    alert(`❌ Rezervasyon başarısız: ${result.reason || result.status}`);
  }
};


// ========================================================
// 🚀 BAŞLANGIÇ YÜKLEMELERİ
// ========================================================
document.getElementById("ev-select").addEventListener("change", updateReservationInfo);
document.getElementById("idle-evse-select").addEventListener("change", updateReservationInfo);

function populateIdleEvseDropdown() {
  loadEvseList();
  updateReservationInfo();
}

loadStatuses();
loadDashboard();
loadEvseList();
populateVehicleDropdown();
populateIdleEvseDropdown();
