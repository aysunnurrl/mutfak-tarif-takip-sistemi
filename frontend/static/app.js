// Global State
let currentUser = null;
let authToken = localStorage.getItem("token") || null;
let cachedRecipes = [];
let cachedMaterials = [];
let cachedEquipments = [];

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  startClock();
  if (authToken) {
    validateSession();
  } else {
    showLogin();
  }
});

// Clock
function startClock() {
  const el = document.getElementById("headerClock");
  setInterval(() => {
    const now = new Date();
    if (el) el.textContent = now.toLocaleDateString("tr-TR") + " " + now.toLocaleTimeString("tr-TR");
  }, 1000);
}

// Quick Test Fill
function fillLogin(kadi, sifre) {
  document.getElementById("kadiInput").value = kadi;
  document.getElementById("sifreInput").value = sifre;
  showToast("Demo kullanıcı dolduruldu!", "info");
}

// Toast Notification
function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  const icon = document.getElementById("toastIcon");
  const title = document.getElementById("toastTitle");
  const msg = document.getElementById("toastMessage");

  if (type === "success") {
    toast.className = "fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 opacity-100 bg-emerald-950/90 border border-emerald-500/40 text-emerald-200 translate-y-0";
    icon.className = "fa-solid fa-circle-check text-emerald-400";
    title.textContent = "İşlem Başarılı";
  } else if (type === "error") {
    toast.className = "fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 opacity-100 bg-rose-950/90 border border-rose-500/40 text-rose-200 translate-y-0";
    icon.className = "fa-solid fa-circle-xmark text-rose-400";
    title.textContent = "Hata Oluştu";
  } else {
    toast.className = "fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl backdrop-blur-md transition-all duration-300 opacity-100 bg-blue-950/90 border border-blue-500/40 text-blue-200 translate-y-0";
    icon.className = "fa-solid fa-circle-info text-blue-400";
    title.textContent = "Bilgi";
  }

  msg.textContent = message;

  setTimeout(() => {
    toast.classList.add("opacity-0", "pointer-events-none", "translate-y-[-20px]");
    toast.classList.remove("opacity-100", "translate-y-0");
  }, 3500);
}

// API Fetch Helper with Auth Header
async function fetchApi(endpoint, options = {}) {
  const headers = options.headers || {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(endpoint, { ...options, headers });
  if (response.status === 401) {
    logout();
    throw new Error("Oturum süresi doldu. Lütfen tekrar giriş yapın.");
  }
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Bilinmeyen bir hata oluştu" }));
    throw new Error(errorData.detail || "İşlem başarısız");
  }
  return response.json();
}

// Login
async function handleLogin(e) {
  e.preventDefault();
  const kadi = document.getElementById("kadiInput").value.trim();
  const sifre = document.getElementById("sifreInput").value.trim();
  const btn = document.getElementById("loginBtn");

  try {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Giriş Yapılıyor...</span>`;

    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kadi, sifre })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Giriş başarısız");
    }

    authToken = data.access_token;
    localStorage.setItem("token", authToken);
    currentUser = data.user;

    showToast(`Hoş geldiniz, ${currentUser.ad} ${currentUser.soyad}! (${currentUser.role_title})`, "success");
    setupRoleUI();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Sisteme Giriş Yap</span><i class="fa-solid fa-arrow-right"></i>`;
  }
}

// Check Session on reload
async function validateSession() {
  try {
    const user = await fetchApi("/api/me");
    currentUser = {
      id: user.sub,
      kadi: user.kadi,
      ad: user.ad,
      soyad: user.soyad,
      role: user.role,
      role_title: user.role_title
    };
    setupRoleUI();
  } catch (err) {
    logout();
  }
}

// Setup Dashboard based on RBAC
function setupRoleUI() {
  document.getElementById("loginView").classList.add("hidden");
  document.getElementById("appView").classList.remove("hidden");

  // User Card in sidebar
  document.getElementById("userFullName").textContent = `${currentUser.ad} ${currentUser.soyad}`;
  document.getElementById("userEmail").textContent = `@${currentUser.kadi}`;
  document.getElementById("userInitials").textContent = `${currentUser.ad[0] || ""}${currentUser.soyad[0] || ""}`.toUpperCase();

  const roleBadge = document.getElementById("userBadgeRole");
  roleBadge.textContent = currentUser.role_title || currentUser.role;

  // Role Color Coding
  const roleColors = {
    yonetici: "bg-purple-950 text-purple-300 border border-purple-700/60",
    asci: "bg-amber-950 text-amber-300 border border-amber-700/60",
    depo: "bg-blue-950 text-blue-300 border border-blue-700/60",
  };
  roleBadge.className = `text-[11px] font-semibold px-2.5 py-0.5 rounded-full inline-block mt-1 ${roleColors[currentUser.role] || "bg-slate-800 text-slate-300"}`;

  // Top bar role security notice
  const notice = document.getElementById("roleSecurityNotice");
  if (currentUser.role === "yonetici") {
    notice.innerHTML = `<i class="fa-solid fa-shield-halved text-purple-400 mr-1"></i> Yönetici Modu: Tam Yetki & Maliyet Denetimi`;
  } else if (currentUser.role === "asci") {
    notice.innerHTML = `<i class="fa-solid fa-kitchen-set text-amber-400 mr-1"></i> Aşçı Modu: Reçete Porsiyonlama & Sıcaklık Kontrolü (Stoklar Gizli)`;
  } else if (currentUser.role === "depo") {
    notice.innerHTML = `<i class="fa-solid fa-warehouse text-blue-400 mr-1"></i> Depo Modu: Stok Giriş/Çıkış & Satınalma Talebi (Maliyetler Gizli)`;
  }

  // RBAC Navigation Menus Visibility
  const navAsci = document.getElementById("navGroupAsci");
  const navDepo = document.getElementById("navGroupDepo");
  const navYonetici = document.getElementById("navGroupYonetici");

  navAsci.classList.add("hidden");
  navDepo.classList.add("hidden");
  navYonetici.classList.add("hidden");

  if (currentUser.role === "yonetici") {
    navYonetici.classList.remove("hidden");
    navDepo.classList.remove("hidden"); // Yönetici stokları da görür
  } else if (currentUser.role === "asci") {
    navAsci.classList.remove("hidden");
  } else if (currentUser.role === "depo") {
    navDepo.classList.remove("hidden");
  }

  // Buton yetkileri (Depocu yeni talep açabilir)
  const openPurchaseBtn = document.getElementById("openPurchaseModalBtn");
  if (currentUser.role === "depo") {
    openPurchaseBtn.classList.remove("hidden");
    openPurchaseBtn.classList.add("flex");
  } else {
    openPurchaseBtn.classList.add("hidden");
    openPurchaseBtn.classList.remove("flex");
  }

  // Varsayılan ilk sekmeyi aç
  if (currentUser.role === "yonetici") {
    switchTab("yoneticiRaporTab");
  } else if (currentUser.role === "asci") {
    switchTab("tariflerTab");
  } else if (currentUser.role === "depo") {
    switchTab("depoStoklarTab");
  } else {
    switchTab("tariflerTab");
  }

  // Ortak verileri yükle
  loadRecipes();
  loadEquipments();
}

function showLogin() {
  document.getElementById("loginView").classList.remove("hidden");
  document.getElementById("appView").classList.add("hidden");
}

function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem("token");
  showLogin();
  showToast("Oturum kapatıldı.", "info");
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.add("hidden"));
  document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));

  const target = document.getElementById(tabId);
  if (target) target.classList.remove("hidden");

  // Nav link highlight
  const navMap = {
    tariflerTab: "nav-tarifler",
    asciSimulasyonTab: "nav-simulasyon",
    asciSicaklikTab: "nav-sicaklik",
    depoStoklarTab: "nav-stoklar",
    depoHareketTab: "nav-hareket",
    satinalmaTab: currentUser?.role === "yonetici" ? "nav-onaylar" : "nav-talep",
    yoneticiRaporTab: "nav-rapor",
    yoneticiKullanicilarTab: "nav-kullanicilar"
  };

  const navId = navMap[tabId];
  if (navId) {
    const navEl = document.getElementById(navId);
    if (navEl) navEl.classList.add("active");
  }

  // Lazy-load veriler
  if (tabId === "tariflerTab") loadRecipes();
  if (tabId === "depoStoklarTab") loadStock();
  if (tabId === "depoHareketTab") { loadStockMovements(); loadStockForDropdowns(); }
  if (tabId === "satinalmaTab") { loadPurchaseRequests(); loadStockForDropdowns(); }
  if (tabId === "yoneticiRaporTab") loadReports();
  if (tabId === "yoneticiKullanicilarTab") loadUsers();
  if (tabId === "asciSimulasyonTab") initSimulator();
}


// --- 1. TARİFLER & REÇETELER ---
async function loadRecipes() {
  const grid = document.getElementById("recipeCardsGrid");
  try {
    const data = await fetchApi("/api/tarifler");
    cachedRecipes = data;

    if (!data.length) {
      grid.innerHTML = `<div class="col-span-full text-center py-12 text-slate-500">Kayıtlı tarif bulunamadı.</div>`;
      return;
    }

    grid.innerHTML = data.map(r => {
      const isYonetici = currentUser?.role === "yonetici";
      const isAsci = currentUser?.role === "asci";

      const costBadge = isYonetici && r.tahmini_maliyet !== undefined
        ? `<div class="mt-3 pt-3 border-t border-slate-800 flex justify-between items-center text-xs">
             <span class="text-slate-400">Reçete Tahmini Maliyeti:</span>
             <span class="font-bold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-lg border border-emerald-800/40">${r.tahmini_maliyet} ₺</span>
           </div>`
        : "";

      const materialsList = r.malzemeler.map(m => {
        const priceInfo = isYonetici && m.birim_fiyat ? `<span class="text-[11px] text-slate-400 font-mono">(${m.birim_fiyat} ₺)</span>` : "";
        return `<li class="flex items-center justify-between py-1 border-b border-slate-800/40 text-xs">
                  <span class="text-slate-300"><i class="fa-solid fa-check text-[10px] text-amber-500 mr-1.5"></i>${m.malzeme_adi}</span>
                  <div class="space-x-1"><span class="text-slate-500">${m.birim}</span> ${priceInfo}</div>
                </li>`;
      }).join("");

      const asciAction = isAsci ? `
        <button onclick="openInSimulator(${r.tarifno})" class="mt-4 w-full py-2 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 border border-amber-500/40 rounded-xl text-xs font-semibold transition flex items-center justify-center gap-2">
          <i class="fa-solid fa-scale-balanced"></i> Bu Tarifi Porsiyonla
        </button>
      ` : "";

      return `
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between hover:border-slate-700 transition">
          <div>
            <div class="flex items-start justify-between gap-2 mb-3">
              <div>
                <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800/50">
                  ${r.kategoriadi || "Mutfak"}
                </span>
                <h4 class="text-base font-bold text-white mt-1">${r.yemekadı || `Tarif #${r.tarifno}`}</h4>
              </div>
              <span class="text-xs bg-slate-800 px-2.5 py-1 rounded-lg text-slate-300 font-mono">
                <i class="fa-regular fa-clock mr-1 text-amber-400"></i>${r.hazırlamasuresi || 30} dk
              </span>
            </div>

            <p class="text-xs text-slate-400 mb-4 line-clamp-2">${r.aciklama || "Aşçı ve şefler için hazırlanmış standart reçete listesi."}</p>

            <div>
              <h5 class="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <i class="fa-solid fa-mortar-pestle text-amber-500"></i> Malzemeler (${r.malzemeler.length})
              </h5>
              <ul class="space-y-0.5 max-h-36 overflow-y-auto pr-1">
                ${materialsList || `<li class="text-xs text-slate-500">Malzeme bilgisi yok.</li>`}
              </ul>
            </div>
          </div>

          <div>
            ${costBadge}
            ${asciAction}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full text-center py-12 text-rose-400">${err.message}</div>`;
  }
}


// --- 2. AŞÇI: PORSİYON SİMÜLATÖRÜ ---
function initSimulator() {
  const select = document.getElementById("simulatorRecipeSelect");
  if (!select) return;
  select.innerHTML = cachedRecipes.map(r => `
    <option value="${r.tarifno}">${r.yemekadı || `Tarif #${r.tarifno}`} (${r.porsiyonbilgisi || "4 Kişilik"})</option>
  `).join("");

  if (cachedRecipes.length) {
    runSimulation();
  }
}

function openInSimulator(tarifno) {
  switchTab("asciSimulasyonTab");
  const select = document.getElementById("simulatorRecipeSelect");
  if (select) {
    select.value = tarifno;
    runSimulation();
  }
}

function updateMultiplier(val) {
  document.getElementById("multiplierValueBadge").textContent = `${val}x`;
  runSimulation();
}

async function runSimulation() {
  const select = document.getElementById("simulatorRecipeSelect");
  const multiplier = document.getElementById("portionMultiplier").value;
  const tno = select.value;
  if (!tno) return;

  const tbody = document.getElementById("simResultsBody");
  tbody.innerHTML = `<tr><td colspan="3" class="text-center py-6 text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Hesaplanıyor...</td></tr>`;

  try {
    const data = await fetchApi(`/api/asci/recete-olcekle/${tno}?carpan=${multiplier}`);
    document.getElementById("simRecipeTitle").textContent = `${data.tarif.yemekadı || "Reçete"} (Ölçek: ${data.hesaplanan_porsiyon})`;
    document.getElementById("simPortionBadge").textContent = `${data.tarif.hazırlamasuresi || 30} dk Hazırlık`;

    tbody.innerHTML = data.malzemeler.map(m => {
      let warningBadge = `<span class="px-2 py-0.5 rounded text-xs bg-emerald-950/60 text-emerald-400 border border-emerald-800/40"><i class="fa-solid fa-check mr-1"></i>${m.stok_uyarisi}</span>`;
      if (m.stok_uyarisi.includes("⚠️")) {
        warningBadge = `<span class="px-2 py-0.5 rounded text-xs bg-amber-950/60 text-amber-300 border border-amber-800/50">${m.stok_uyarisi}</span>`;
      }
      return `
        <tr class="hover:bg-slate-800/40">
          <td class="px-4 py-3 font-medium text-white">${m.malzeme_adi}</td>
          <td class="px-4 py-3 font-mono font-bold text-amber-400">${m.hesaplanan_miktar}</td>
          <td class="px-4 py-3">${warningBadge}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="3" class="text-center py-6 text-rose-400">${err.message}</td></tr>`;
  }
}


// --- 3. AŞÇI: SICAKLIK KONTROLÜ ---
async function loadEquipments() {
  try {
    const data = await fetchApi("/api/asci/ekipmanlar");
    cachedEquipments = data;
    const select = document.getElementById("tempEquipmentSelect");
    if (select) {
      select.innerHTML = data.map(e => `
        <option value="${e.ekipmanid}">${e.ekipmanadı} (${e.markaadı || "Mutfak"})</option>
      `).join("");
    }
  } catch (err) {
    console.error(err);
  }
}

async function handleTempSubmit(e) {
  e.preventDefault();
  const ekipmanid = parseInt(document.getElementById("tempEquipmentSelect").value);
  const olculensicaklik = document.getElementById("tempValueInput").value;

  try {
    const res = await fetchApi("/api/asci/sicaklik-kaydi", {
      method: "POST",
      body: JSON.stringify({ ekipmanid, olculensicaklik })
    });
    showToast(res.message, "success");
    document.getElementById("tempValueInput").value = "";
  } catch (err) {
    showToast(err.message, "error");
  }
}


// --- 4. DEPO: STOK TAKİBİ & HAREKETLER ---
async function loadStock() {
  const tbody = document.getElementById("stockTableBody");
  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Stoklar yükleniyor...</td></tr>`;

  try {
    const data = await fetchApi("/api/depo/stoklar");
    cachedMaterials = data;

    tbody.innerHTML = data.map(m => {
      const guncel = m.guncel_stok;
      const min = parseInt(m.MinStokSeviyesi) || 0;
      const isCritical = guncel <= min;

      const badge = isCritical 
        ? `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-800/50">Kritik Stok</span>`
        : `<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">Normal</span>`;

      const action = currentUser?.role === "depo" && isCritical
        ? `<button onclick="quickPurchaseRequest(${m.malzemeid})" class="px-3 py-1 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 border border-amber-500/40 rounded-lg text-xs font-semibold transition">
             Talep Aç
           </button>`
        : "";

      return `
        <tr class="hover:bg-slate-800/40">
          <td class="px-5 py-3.5 font-mono text-xs text-slate-400">#${m.malzemeid}</td>
          <td class="px-5 py-3.5 font-medium text-white">${m.malzeme_adi}</td>
          <td class="px-5 py-3.5 text-xs text-slate-400">${m.skt ? new Date(m.skt).toLocaleDateString("tr-TR") : "--"}</td>
          <td class="px-5 py-3.5 text-xs font-mono text-slate-400">${min}</td>
          <td class="px-5 py-3.5 text-sm font-bold font-mono ${isCritical ? 'text-rose-400' : 'text-slate-200'}">${guncel}</td>
          <td class="px-5 py-3.5">${badge}</td>
          <td class="px-5 py-3.5 text-right">${action}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose-400">${err.message}</td></tr>`;
  }
}

async function loadStockForDropdowns() {
  if (!cachedMaterials.length) {
    try {
      cachedMaterials = await fetchApi("/api/depo/stoklar");
    } catch (e) {
      return;
    }
  }
  const movSelect = document.getElementById("movementMaterialSelect");
  const purSelect = document.getElementById("purchaseMaterialSelect");

  const opts = cachedMaterials.map(m => `<option value="${m.malzemeid}">${m.malzeme_adi}</option>`).join("");
  if (movSelect) movSelect.innerHTML = opts;
  if (purSelect) purSelect.innerHTML = opts;
}

async function loadStockMovements() {
  const tbody = document.getElementById("movementsHistoryBody");
  try {
    const data = await fetchApi("/api/depo/stok-hareketleri");
    tbody.innerHTML = data.map(h => {
      let typeBadge = `<span class="px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">${h.islemTipi}</span>`;
      if (h.islemTipi === "Giriş") typeBadge = `<span class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">Giriş (+)</span>`;
      if (h.islemTipi === "Çıkış") typeBadge = `<span class="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">Çıkış (-)</span>`;
      if (h.islemTipi === "Fire") typeBadge = `<span class="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">Fire ⚠️</span>`;

      return `
        <tr class="hover:bg-slate-800/40">
          <td class="px-3 py-2 font-mono text-slate-500">#${h.hareketid}</td>
          <td class="px-3 py-2 text-white font-medium">${h.malzeme_adi}</td>
          <td class="px-3 py-2">${typeBadge}</td>
          <td class="px-3 py-2 font-mono font-bold">${h.miktar}</td>
          <td class="px-3 py-2 text-slate-400">${h.personel_adi ? `${h.personel_adi} ${h.personel_soyadi || ""}` : "Sistem"}</td>
          <td class="px-3 py-2 text-slate-500">${new Date(h.tarihSaat).toLocaleDateString("tr-TR")}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-rose-400">${err.message}</td></tr>`;
  }
}

async function handleStockMovementSubmit(e) {
  e.preventDefault();
  const malzemeid = parseInt(document.getElementById("movementMaterialSelect").value);
  const islemTipi = document.getElementById("movementTypeSelect").value;
  const miktar = parseInt(document.getElementById("movementAmountInput").value);
  const aciklama = document.getElementById("movementDescInput").value;

  try {
    const res = await fetchApi("/api/depo/stok-hareketi-ekle", {
      method: "POST",
      body: JSON.stringify({ malzemeid, islemTipi, miktar, aciklama })
    });
    showToast(res.message, "success");
    document.getElementById("movementAmountInput").value = "";
    document.getElementById("movementDescInput").value = "";
    loadStockMovements();
  } catch (err) {
    showToast(err.message, "error");
  }
}


// --- 5. SATINALMA TALEPLERİ & YÖNETİCİ ONAYI ---
async function loadPurchaseRequests() {
  const tbody = document.getElementById("purchaseTableBody");
  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Talepler yükleniyor...</td></tr>`;

  try {
    const data = await fetchApi("/api/satinalma-talepleri");
    const isYonetici = currentUser?.role === "yonetici";

    tbody.innerHTML = data.map(p => {
      let statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950/80 text-amber-300 border border-amber-800/50">Beklemede</span>`;
      if (p.durum === "Onaylandı") statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">Onaylandı</span>`;
      if (p.durum === "Reddedildi") statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-800/50">Reddedildi</span>`;

      let action = `<span class="text-xs text-slate-500 font-mono">-</span>`;
      if (isYonetici && p.durum === "Beklemede") {
        action = `
          <div class="flex items-center justify-end gap-1.5">
            <button onclick="approvePurchase(${p.talepid}, 'Onaylandı')" class="px-2.5 py-1 bg-emerald-500/20 hover:bg-emerald-500 text-emerald-300 hover:text-slate-950 rounded-lg text-xs font-bold transition">
              Onayla
            </button>
            <button onclick="approvePurchase(${p.talepid}, 'Reddedildi')" class="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500 text-rose-300 hover:text-white rounded-lg text-xs font-bold transition">
              Reddet
            </button>
          </div>
        `;
      }

      return `
        <tr class="hover:bg-slate-800/40">
          <td class="px-5 py-3.5 font-mono text-xs text-slate-400">#${p.talepid}</td>
          <td class="px-5 py-3.5 font-medium text-white">${p.talep_eden_ad} ${p.talep_eden_soyad || ""}</td>
          <td class="px-5 py-3.5 text-slate-300">${p.malzeme_adi || "Genel"}</td>
          <td class="px-5 py-3.5 font-mono font-bold text-amber-400">${p.miktar}</td>
          <td class="px-5 py-3.5 text-xs text-slate-400">${p.talepTarihi ? new Date(p.talepTarihi).toLocaleDateString("tr-TR") : "--"}</td>
          <td class="px-5 py-3.5">${statusBadge}</td>
          <td class="px-5 py-3.5 text-right">${action}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose-400">${err.message}</td></tr>`;
  }
}

async function approvePurchase(talepid, durum) {
  try {
    const res = await fetchApi(`/api/yonetici/satinalma-onayla/${talepid}`, {
      method: "PUT",
      body: JSON.stringify({ durum })
    });
    showToast(res.message, "success");
    loadPurchaseRequests();
    if (currentUser?.role === "yonetici") loadReports();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openNewPurchaseModal() {
  document.getElementById("newPurchaseModal").classList.remove("hidden");
  loadStockForDropdowns();
}

function closeNewPurchaseModal() {
  document.getElementById("newPurchaseModal").classList.add("hidden");
}

function quickPurchaseRequest(malzemeid) {
  openNewPurchaseModal();
  const select = document.getElementById("purchaseMaterialSelect");
  if (select) select.value = malzemeid;
}

async function handleCreatePurchase(e) {
  e.preventDefault();
  const malzemeid = parseInt(document.getElementById("purchaseMaterialSelect").value);
  const miktar = document.getElementById("purchaseAmountInput").value;

  try {
    const res = await fetchApi("/api/depo/satinalma-talebi", {
      method: "POST",
      body: JSON.stringify({ malzemeid, miktar })
    });
    showToast(res.message, "success");
    closeNewPurchaseModal();
    loadPurchaseRequests();
  } catch (err) {
    showToast(err.message, "error");
  }
}


// --- 6. YÖNETİCİ: RAPORLAR & İSTATİSTİKLER ---
async function loadReports() {
  try {
    const data = await fetchApi("/api/yonetici/raporlar");
    document.getElementById("statTotalUsers").textContent = data.total_users;
    document.getElementById("statTotalRecipes").textContent = data.total_recipes;
    document.getElementById("statPendingOrders").textContent = data.pending_orders;
    document.getElementById("statTotalWaste").textContent = data.total_waste;

    const tbody = document.getElementById("criticalTempTableBody");
    if (!data.kritik_sicakliklar.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-slate-500">Kritik sıcaklık uyarısı bulunmamaktadır. Tüm ekipmanlar stabil.</td></tr>`;
    } else {
      tbody.innerHTML = data.kritik_sicakliklar.map(s => `
        <tr class="hover:bg-slate-800/40">
          <td class="px-4 py-2.5 font-medium text-white">${s.ekipman}</td>
          <td class="px-4 py-2.5 font-bold font-mono text-rose-400">${s.sicaklik}°C ⚠️</td>
          <td class="px-4 py-2.5 text-slate-300">${s.olcen}</td>
          <td class="px-4 py-2.5 text-slate-400 font-mono">${new Date(s.tarihSaat).toLocaleDateString("tr-TR")}</td>
        </tr>
      `).join("");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}


// --- 7. YÖNETİCİ: KULLANICI YÖNETİMİ ---
async function loadUsers() {
  const tbody = document.getElementById("usersTableBody");
  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Kullanıcılar yükleniyor...</td></tr>`;

  try {
    const data = await fetchApi("/api/yonetici/kullanicilar");
    tbody.innerHTML = data.map(u => {
      let roleBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">${u.rol_adi}</span>`;
      if (u.rol_adi === "Yönetici") roleBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-950 text-purple-300 border border-purple-800/60">Yönetici</span>`;
      if (u.rol_adi === "Aşçı") roleBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800/60">Aşçı</span>`;
      if (u.rol_adi === "Depo Sorumlusu") roleBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-950 text-blue-300 border border-blue-800/60">Depo Sorumlusu</span>`;

      return `
        <tr class="hover:bg-slate-800/40">
          <td class="px-4 py-3 font-mono text-xs text-slate-400">#${u.kullaniciid}</td>
          <td class="px-4 py-3 font-bold text-white font-mono">@${u.kadi}</td>
          <td class="px-4 py-3 text-slate-200">${u.ad} ${u.soyad}</td>
          <td class="px-4 py-3">${roleBadge}</td>
          <td class="px-4 py-3 text-xs text-slate-400">${u.email || "-"} / ${u.telefon || "-"}</td>
          <td class="px-4 py-3 text-xs text-slate-500">${u.isebaslamatarihi ? new Date(u.isebaslamatarihi).toLocaleDateString("tr-TR") : "--"}</td>
          <td class="px-4 py-3 text-right">
            <button onclick="deleteUser(${u.kullaniciid}, '${u.kadi}')" class="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-950/50 rounded-lg transition" title="Kullanıcıyı Sil">
              <i class="fa-regular fa-trash-can"></i>
            </button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose-400">${err.message}</td></tr>`;
  }
}

function openNewUserModal() {
  document.getElementById("newUserModal").classList.remove("hidden");
}

function closeNewUserModal() {
  document.getElementById("newUserModal").classList.add("hidden");
}

function toggleRoleFields(role) {
  const extra = document.getElementById("yoneticiExtraField");
  if (role === "yonetici") {
    extra.classList.remove("hidden");
  } else {
    extra.classList.add("hidden");
  }
}

async function handleCreateUser(e) {
  e.preventDefault();
  const ad = document.getElementById("newAd").value;
  const soyad = document.getElementById("newSoyad").value;
  const kadi = document.getElementById("newKadi").value;
  const sifre = document.getElementById("newSifre").value;
  const role = document.getElementById("newRole").value;
  const email = document.getElementById("newEmail").value;
  const telefon = document.getElementById("newTel").value;
  const butceYetkisiLimiti = parseInt(document.getElementById("newButce").value) || 50000;

  try {
    const res = await fetchApi("/api/yonetici/kullanici-ekle", {
      method: "POST",
      body: JSON.stringify({
        ad, soyad, kadi, sifre, role, email, telefon,
        butceYetkisiLimiti, departmanid: 1, depoid: 1
      })
    });
    showToast(res.message, "success");
    closeNewUserModal();
    loadUsers();
    loadReports();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteUser(kullaniciid, kadi) {
  if (!confirm(`'${kadi}' adlı personeli sistemden silmek istediğinize emin misiniz?`)) return;

  try {
    const res = await fetchApi(`/api/yonetici/kullanici-sil/${kullaniciid}`, {
      method: "DELETE"
    });
    showToast(res.message, "success");
    loadUsers();
    loadReports();
  } catch (err) {
    showToast(err.message, "error");
  }
}
