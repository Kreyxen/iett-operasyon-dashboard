const API = "http://127.0.0.1:8000";
const RENK = { "Hafta İçi": "#3987e5", "Hafta Sonu": "#d95926" };

// --- Tema (aydınlık/karanlık) ---
const TILE_URL = {
  dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  light: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
};
let aktifTema = document.documentElement.getAttribute("data-theme") || "dark";
const TUM_HARITALAR = [];
const TUM_GRAFIKLER = [];

function grafikSecenekleri() {
  const cssRenk = (isim) => getComputedStyle(document.documentElement).getPropertyValue(isim).trim();
  return {
    responsive: true,
    plugins: { legend: { labels: { color: cssRenk("--text-dim") } } },
    scales: {
      x: { ticks: { color: cssRenk("--chart-tick") }, grid: { color: cssRenk("--chart-grid") } },
      y: { ticks: { color: cssRenk("--chart-tick") }, grid: { color: cssRenk("--chart-grid") } },
    },
  };
}

const _ChartOrijinal = Chart;
window.Chart = function (...args) {
  const c = new _ChartOrijinal(...args);
  TUM_GRAFIKLER.push(c);
  return c;
};
window.Chart.prototype = _ChartOrijinal.prototype;

function grafikleriTemayaGoreGuncelle() {
  const secenek = grafikSecenekleri();
  TUM_GRAFIKLER.forEach((c) => {
    if (!c.options) return;
    if (c.options.plugins?.legend?.labels) c.options.plugins.legend.labels.color = secenek.plugins.legend.labels.color;
    if (c.options.scales?.x) { c.options.scales.x.ticks.color = secenek.scales.x.ticks.color; c.options.scales.x.grid.color = secenek.scales.x.grid.color; }
    if (c.options.scales?.y) { c.options.scales.y.ticks.color = secenek.scales.y.ticks.color; c.options.scales.y.grid.color = secenek.scales.y.grid.color; }
    c.update();
  });
}

function hizRengi(hiz) {
  if (hiz < 5) return "#e34948";
  if (hiz < 25) return "#eda100";
  return "#1baf7a";
}

function koyuHarita(elementId, merkez = [41.01, 29.0], zoom = 11) {
  const harita = L.map(elementId).setView(merkez, zoom);
  harita._karoKatmani = L.tileLayer(TILE_URL[aktifTema], {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
    maxZoom: 19,
  }).addTo(harita);
  TUM_HARITALAR.push(harita);
  return harita;
}

function temayiUygula(tema) {
  aktifTema = tema;
  document.documentElement.setAttribute("data-theme", tema);
  localStorage.setItem("iett-tema", tema);
  document.getElementById("tema-buton").textContent = tema === "dark" ? "🌙" : "☀️";
  TUM_HARITALAR.forEach((h) => h._karoKatmani?.setUrl(TILE_URL[tema]));
  grafikleriTemayaGoreGuncelle();
}

document.getElementById("tema-buton").addEventListener("click", () => {
  temayiUygula(aktifTema === "dark" ? "light" : "dark");
});
temayiUygula(aktifTema);

// --- Nav geçişleri ---
const yuklenenSekmeler = new Set();
const YUKLEYICILER = {
  genel: genelBakisYukle,
  verimlilik: verimlilikYukle,
  ariza: arizaYukle,
  filo: filoYukle,
  yogunluk: yogunlukYukle,
  duyurular: duyurularYukle,
  kaza: kazaYukle,
  planauyum: planaUyumYukle,
};

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const hedef = btn.dataset.section;
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("aktif"));
    document.querySelectorAll(".sayfa").forEach((s) => s.classList.remove("aktif"));
    btn.classList.add("aktif");
    document.getElementById(`sayfa-${hedef}`).classList.add("aktif");
    if (!yuklenenSekmeler.has(hedef)) {
      yuklenenSekmeler.add(hedef);
      YUKLEYICILER[hedef]?.().catch((e) => console.error(hedef, e));
    }
  });
});

// --- Bağlantı durumu (backend ayakta mı) -- üst bardaki pill'de gösterilir ---
const canliPill = document.getElementById("canli-pill");
const canliPillMetin = document.getElementById("canli-pill-metin");

async function baglantiyiKontrolEt() {
  try {
    await fetch(`${API}/api/ozet`);
    canliPill.classList.remove("koptu");
    canliPillMetin.textContent = "Canlı Veri Akışı";
  } catch {
    canliPill.classList.add("koptu");
    canliPillMetin.textContent = "Backend'e Ulaşılamıyor";
  }
}
baglantiyiKontrolEt();
setInterval(baglantiyiKontrolEt, 30_000);

// --- Genel Bakış ---
async function genelBakisYukle() {
  const ozet = await fetch(`${API}/api/ozet`).then((r) => r.json());
  document.getElementById("kpi-arac").textContent = ozet.canli_arac.toLocaleString("tr-TR");
  document.getElementById("kpi-hiz").textContent = `${ozet.ortalama_hiz} km/h`;
  document.getElementById("kpi-duyuru").textContent = ozet.aktif_duyuru;
  document.getElementById("guncelleme-saati").textContent = ozet.guncelleme;
  document.getElementById("zil-rozet").textContent = ozet.aktif_duyuru;

  const trafik = await fetch(`${API}/api/trafik?gun=3`).then((r) => r.json());
  const trafikSirali = [...trafik].sort((a, b) => new Date(a.TrafficIndexDate) - new Date(b.TrafficIndexDate));
  document.getElementById("kpi-trafik").textContent = trafikSirali.at(-1)?.TrafficIndex ?? "—";

  new Chart(document.getElementById("trafik-grafik-genel"), {
    type: "line",
    data: {
      labels: trafikSirali.map((d) => new Date(d.TrafficIndexDate).toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", hour: "2-digit" })),
      datasets: [{ label: "Trafik İndeksi", data: trafikSirali.map((d) => d.TrafficIndex), borderColor: "#3987e5", backgroundColor: "#3987e522", tension: 0.3, fill: true, pointRadius: 2 }],
    },
    options: grafikSecenekleri(),
  });

  const yogunluk = await fetch(`${API}/api/yogunluk`).then((r) => r.json());
  cizYogunlukGrafigi("yogunluk-grafik-genel", yogunluk.saatlik);

  setInterval(async () => {
    const o = await fetch(`${API}/api/ozet`).then((r) => r.json());
    document.getElementById("kpi-arac").textContent = o.canli_arac.toLocaleString("tr-TR");
    document.getElementById("kpi-hiz").textContent = `${o.ortalama_hiz} km/h`;
    document.getElementById("kpi-duyuru").textContent = o.aktif_duyuru;
    document.getElementById("guncelleme-saati").textContent = o.guncelleme;
    document.getElementById("zil-rozet").textContent = o.aktif_duyuru;
  }, 60_000);
}

function cizYogunlukGrafigi(canvasId, yogunluk) {
  const saatler = [...new Set(yogunluk.map((d) => d.transition_hour))].sort((a, b) => a - b);
  return new Chart(document.getElementById(canvasId), {
    type: "line",
    data: {
      labels: saatler,
      datasets: ["Hafta İçi", "Hafta Sonu"].map((gt) => ({
        label: gt,
        data: saatler.map((s) => yogunluk.find((d) => d.transition_hour === s && d.gun_tipi === gt)?.ortalama_yolcu ?? null),
        borderColor: RENK[gt],
        backgroundColor: RENK[gt] + "22",
        tension: 0.3,
        pointRadius: 2,
      })),
    },
    options: grafikSecenekleri(),
  });
}

// --- Verimlilik ---
const TIP_RENK = { ana_arter: "#3987e5", orta_yogunluklu: "#d95926", tali_kucuk: "#199e70", uzun_kirsal: "#c98500" };
const TIER_ETIKET = { alt_ceyrek: "Alt Çeyrek", orta_alt: "Orta Alt", orta_ust: "Orta Üst", ust_ceyrek: "Üst Çeyrek" };
const TIP_ETIKET = { ana_arter: "Ana Arter", orta_yogunluklu: "Orta Yoğunluklu", tali_kucuk: "Tali Küçük", uzun_kirsal: "Uzun Kırsal" };
const TIER_SIRA = ["alt_ceyrek", "orta_alt", "orta_ust", "ust_ceyrek"];
let verimlilikVeri = [];
let verimlilikGrafikleri = {};
const aktifTierler = new Set(TIER_SIRA);
const aktifTipler = new Set(Object.keys(TIP_ETIKET));

function verimlilikCipleriKur() {
  document.getElementById("tier-filtre").innerHTML = TIER_SIRA.map(
    (t) => `<button type="button" class="cip aktif" data-tier="${t}">${TIER_ETIKET[t]}</button>`
  ).join("");
  document.getElementById("tip-filtre").innerHTML = Object.keys(TIP_ETIKET).map(
    (t) => `<button type="button" class="cip aktif" data-tip="${t}">${TIP_ETIKET[t]}</button>`
  ).join("");

  document.querySelectorAll("#tier-filtre .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      cip.classList.toggle("aktif");
      const t = cip.dataset.tier;
      cip.classList.contains("aktif") ? aktifTierler.add(t) : aktifTierler.delete(t);
      verimlilikUygula();
    });
  });
  document.querySelectorAll("#tip-filtre .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      cip.classList.toggle("aktif");
      const t = cip.dataset.tip;
      cip.classList.contains("aktif") ? aktifTipler.add(t) : aktifTipler.delete(t);
      verimlilikUygula();
    });
  });
  document.getElementById("supheli-checkbox").addEventListener("change", verimlilikUygula);
  document.getElementById("verimlilik-arama").addEventListener("input", verimlilikUygula);
}

function verimlilikFiltreliVeri() {
  const supheliHaric = document.getElementById("supheli-checkbox").checked;
  const arama = document.getElementById("verimlilik-arama").value.toLowerCase();
  return verimlilikVeri.filter((h) => {
    if (!aktifTierler.has(h.verimlilik_tier) || !aktifTipler.has(h.hat_tipi_ad)) return false;
    if (supheliHaric && h.supheli_kod_eslesmesi) return false;
    if (arama && !String(h.hat_kodu).toLowerCase().includes(arama) && !String(h.SHATADI).toLowerCase().includes(arama)) return false;
    return true;
  });
}

function verimlilikUygula() {
  const filtreli = verimlilikFiltreliVeri();
  document.getElementById("verimlilik-gosterilen").textContent = `${filtreli.length} hat gösteriliyor`;
  verimlilikTabloCiz(filtreli);
  verimlilikGrafikleriCiz(filtreli);
}

async function verimlilikYukle() {
  verimlilikVeri = await fetch(`${API}/api/verimlilik`).then((r) => r.json());
  document.getElementById("kpi-hat-sayisi").textContent = verimlilikVeri.length;
  document.getElementById("kpi-ust-ceyrek").textContent = verimlilikVeri.filter((h) => h.verimlilik_tier === "ust_ceyrek").length;

  verimlilikCipleriKur();
  verimlilikUygula();

  const hatlar = [...new Map(verimlilikVeri.map((h) => [String(h.hat_kodu), h.SHATADI])).entries()].sort((a, b) => a[0].localeCompare(b[0]));
  const secim = document.getElementById("guzergah-hat-secim");
  secim.innerHTML = hatlar.map(([kod, ad]) => `<option value="${kod}">${kod} — ${ad}</option>`).join("");
  secim.addEventListener("change", () => guzergahYukle(secim.value));
  if (hatlar.length) guzergahYukle(hatlar[0][0]);
}

function verimlilikTabloCiz(veri) {
  const tablo = document.getElementById("verimlilik-tablo");
  tablo.querySelector("thead").innerHTML = "<tr><th>Hat</th><th>Ad</th><th>Tier</th><th>Tip</th><th>Yolcu/km</th></tr>";
  tablo.querySelector("tbody").innerHTML = veri
    .slice(0, 200)
    .map((h) => `<tr><td>${h.hat_kodu}</td><td>${h.SHATADI}</td><td>${h.verimlilik_tier}</td><td>${h.hat_tipi_ad}</td><td>${h.ortalama_oran.toFixed(2)}</td></tr>`)
    .join("");
}

function verimlilikGrafikleriCiz(veri) {
  Object.values(verimlilikGrafikleri).forEach((g) => g.destroy());

  const tipGruplari = {};
  veri.forEach((h) => {
    tipGruplari[h.hat_tipi_ad] ??= [];
    tipGruplari[h.hat_tipi_ad].push({ x: h.HAT_UZUNLUGU, y: h.ortalama_oran });
  });

  verimlilikGrafikleri.scatter = new Chart(document.getElementById("verimlilik-scatter"), {
    type: "scatter",
    data: {
      datasets: Object.entries(tipGruplari).map(([tip, noktalar]) => ({
        label: TIP_ETIKET[tip] || tip,
        data: noktalar,
        backgroundColor: TIP_RENK[tip] || "#888",
        pointRadius: 3,
      })),
    },
    options: {
      ...grafikSecenekleri(),
      scales: {
        x: { title: { display: true, text: "Hat uzunluğu (km)", color: "#8b8d94" }, ticks: { color: "#8b8d94" }, grid: { color: "#2c2c2a" } },
        y: { title: { display: true, text: "Yolcu/km oranı", color: "#8b8d94" }, ticks: { color: "#8b8d94" }, grid: { color: "#2c2c2a" } },
      },
    },
  });

  const tierSayim = TIER_SIRA.map((t) => veri.filter((h) => h.verimlilik_tier === t).length);
  verimlilikGrafikleri.tierBar = new Chart(document.getElementById("verimlilik-tier-bar"), {
    type: "bar",
    data: {
      labels: TIER_SIRA.map((t) => TIER_ETIKET[t]),
      datasets: [{ data: tierSayim, backgroundColor: ["#3987e5", "#199e70", "#d95926", "#c98500"] }],
    },
    options: { ...grafikSecenekleri(), plugins: { legend: { display: false } } },
  });

  const tipler = Object.keys(TIP_ETIKET).filter((t) => tipGruplari[t]?.length);
  verimlilikGrafikleri.tipAralik = new Chart(document.getElementById("verimlilik-tip-aralik"), {
    type: "bar",
    data: {
      labels: tipler.map((t) => TIP_ETIKET[t]),
      datasets: [{
        label: "Min–Maks oran",
        data: tipler.map((t) => {
          const oranlar = tipGruplari[t].map((n) => n.y);
          return [Math.min(...oranlar), Math.max(...oranlar)];
        }),
        backgroundColor: tipler.map((t) => TIP_RENK[t]),
      }],
    },
    options: { ...grafikSecenekleri(), plugins: { legend: { display: false } } },
  });
}

// --- Verimlilik: Güzergah haritası ---
let guzergahHaritasi;
const YON_RENK = { G: "#3987e5", D: "#eb6834" };
const YON_ETIKET = { G: "Gidiş", D: "Dönüş" };
const ESIK_DERECE = 150 / 100_000;

function enYakinMesafe(nokta, duraklar) {
  let enKucuk = Infinity;
  for (const d of duraklar) {
    const fark = Math.hypot(nokta[0] - d.enlem, nokta[1] - d.boylam);
    if (fark < enKucuk) enKucuk = fark;
  }
  return enKucuk;
}

async function guzergahYukle(hatKodu) {
  const veri = await fetch(`${API}/api/guzergah?hat=${encodeURIComponent(hatKodu)}`).then((r) => r.json());
  if (!veri.length) {
    document.getElementById("guzergah-ozet").textContent = "Bu hat için güzergah verisi bulunamadı.";
    document.getElementById("guzergah-durak-liste").innerHTML = "";
    document.getElementById("guzergah-yon-secim").innerHTML = "";
    return;
  }
  const yonler = [...new Set(veri.map((d) => d.YON))];
  document.getElementById("guzergah-yon-secim").innerHTML = yonler.map(
    (y, i) => `<button type="button" class="cip ${i === 0 ? "aktif" : ""}" data-yon="${y}">${YON_ETIKET[y] || y}</button>`
  ).join("");
  document.querySelectorAll("#guzergah-yon-secim .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      document.querySelectorAll("#guzergah-yon-secim .cip").forEach((c) => c.classList.remove("aktif"));
      cip.classList.add("aktif");
      guzergahYonCiz(veri, cip.dataset.yon);
    });
  });
  guzergahYonCiz(veri, yonler[0]);
}

async function guzergahYonCiz(veri, yon) {
  const duraklar = veri.filter((d) => d.YON === yon).sort((a, b) => a.SIRANO - b.SIRANO);
  document.getElementById("guzergah-ozet").textContent =
    `Kalkış: ${duraklar[0].DURAKADI} → Varış: ${duraklar.at(-1).DURAKADI} (${duraklar.length} durak)`;

  document.getElementById("guzergah-durak-liste").innerHTML = duraklar.map(
    (d, i) => `<button type="button" class="guzergah-durak-satir" data-index="${i}">${d.SIRANO}. ${d.DURAKADI}</button>`
  ).join("");

  if (!guzergahHaritasi) guzergahHaritasi = koyuHarita("guzergah-harita");
  if (guzergahHaritasi._rota) guzergahHaritasi.removeLayer(guzergahHaritasi._rota);
  const grup = L.layerGroup().addTo(guzergahHaritasi);
  guzergahHaritasi._rota = grup;

  L.polyline(duraklar.map((d) => [d.enlem, d.boylam]), { color: YON_RENK[yon] || "#199e70", weight: 4, opacity: 0.9 }).addTo(grup);
  const durakMarkerlari = duraklar.map((d) =>
    L.circleMarker([d.enlem, d.boylam], { radius: 3, color: "#c3c2b7", fillColor: "#fff", fillOpacity: 0.9, weight: 1 })
      .bindPopup(d.DURAKADI)
      .addTo(grup)
  );
  guzergahHaritasi.fitBounds(duraklar.map((d) => [d.enlem, d.boylam]));

  let seciliMarker = null;
  document.querySelectorAll(".guzergah-durak-satir").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".guzergah-durak-satir").forEach((b) => b.classList.remove("secili"));
      btn.classList.add("secili");
      if (seciliMarker) seciliMarker.setStyle({ radius: 3, color: "#c3c2b7", fillColor: "#fff", weight: 1 });
      const i = Number(btn.dataset.index);
      const d = duraklar[i];
      seciliMarker = durakMarkerlari[i];
      seciliMarker.setStyle({ radius: 11, color: "#0d366b", fillColor: "#e34948", weight: 2 });
      seciliMarker.bringToFront();
      guzergahHaritasi.setView([d.enlem, d.boylam], 16);
    });
  });

  // Arıza / kaza kesişimi -- Streamlit'teki 150m eşiğiyle aynı basit mesafe hesabı.
  const [arizaVerisi, kazaVerisi] = await Promise.all([
    fetch(`${API}/api/ariza`).then((r) => r.json()),
    fetch(`${API}/api/kaza`).then((r) => r.json()),
  ]);
  const yakinAriza = arizaVerisi.filter((a) => enYakinMesafe([a.NENLEM, a.NBOYLAM], duraklar) <= ESIK_DERECE);
  const yakinKaza = kazaVerisi.filter((k) => enYakinMesafe([k.ENLEM, k.BOYLAM], duraklar) <= ESIK_DERECE);

  let uyariHtml = "";
  if (yakinKaza.length) uyariHtml += `<div class="kesisim-uyari kaza">🚨 Bu güzergahın ~150m yakınında son 14 günde <b>${yakinKaza.length}</b> kaza kaydı var.</div>`;
  if (yakinAriza.length) uyariHtml += `<div class="kesisim-uyari ariza">⚠️ Bu güzergahın ~150m yakınında <b>${yakinAriza.length}</b> aktif arıza bildirimi var.</div>`;
  document.getElementById("guzergah-kesisim-uyari").innerHTML = uyariHtml;
}

// --- Arıza Takip ---
const KAYNAK_RENK = { "Sistem (İETT)": "#e34948", "Sentetik (Demo)": "#8b8d94", "Manuel Bildirim": "#3987e5" };

const ISI_HARITA_AYARLARI = {
  radius: 30,
  blur: 25,
  minOpacity: 0.45,
  max: 0.6,
  gradient: { 0.2: "#3987e5", 0.4: "#199e70", 0.6: "#eda100", 0.8: "#d95926", 1.0: "#e34948" },
};

function noktaIkonu(renk, yaricap = 5) {
  return L.divIcon({
    className: "",
    html: `<div style="width:${yaricap * 2}px;height:${yaricap * 2}px;border-radius:50%;background:${renk};border:1px solid #0f1115cc;"></div>`,
    iconSize: [yaricap * 2, yaricap * 2],
  });
}

let arizaHaritasi, arizaVeriTumu = [];
const aktifArizaKaynaklari = new Set();
let arizaGorunum = "nokta";

function arizaHaritayiCiz() {
  const secili = arizaVeriTumu.filter((a) => aktifArizaKaynaklari.has(a.kaynak));
  document.getElementById("kpi-ariza-toplam").textContent = secili.length;
  const kumeSayisi = new Set(secili.filter((a) => a.kume_id !== -1).map((a) => a.kume_id)).size;
  document.getElementById("kpi-ariza-kume").textContent = kumeSayisi;

  if (!arizaHaritasi) arizaHaritasi = koyuHarita("ariza-harita");
  if (arizaHaritasi._kume) arizaHaritasi.removeLayer(arizaHaritasi._kume);
  if (arizaHaritasi._isi) arizaHaritasi.removeLayer(arizaHaritasi._isi);

  if (arizaGorunum === "isi") {
    arizaHaritasi._isi = L.heatLayer(secili.map((a) => [a.NENLEM, a.NBOYLAM]), ISI_HARITA_AYARLARI).addTo(arizaHaritasi);
    return;
  }

  const kume = L.markerClusterGroup({ maxClusterRadius: 45 });
  secili.forEach((a) => {
    L.marker([a.NENLEM, a.NBOYLAM], { icon: noktaIkonu(KAYNAK_RENK[a.kaynak] || "#888") })
      .bindPopup(`<b>${a.kaynak}</b><br>${a.SMESAJMETNI}<br>${a.zaman}`)
      .addTo(kume);
  });
  arizaHaritasi.addLayer(kume);
  arizaHaritasi._kume = kume;
}

async function arizaYukle() {
  arizaVeriTumu = await fetch(`${API}/api/ariza`).then((r) => r.json());
  const kaynaklar = [...new Set(arizaVeriTumu.map((a) => a.kaynak))];
  kaynaklar.forEach((k) => aktifArizaKaynaklari.add(k));

  document.getElementById("ariza-kaynak-filtre").innerHTML = kaynaklar.map(
    (k) => `<button type="button" class="cip aktif" data-kaynak="${k}">${k}</button>`
  ).join("");
  document.querySelectorAll("#ariza-kaynak-filtre .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      cip.classList.toggle("aktif");
      const k = cip.dataset.kaynak;
      cip.classList.contains("aktif") ? aktifArizaKaynaklari.add(k) : aktifArizaKaynaklari.delete(k);
      arizaHaritayiCiz();
    });
  });

  document.querySelectorAll("#ariza-gorunum-secim .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      document.querySelectorAll("#ariza-gorunum-secim .cip").forEach((c) => c.classList.remove("aktif"));
      cip.classList.add("aktif");
      arizaGorunum = cip.dataset.gorunum;
      arizaHaritayiCiz();
    });
  });

  arizaHaritayiCiz();
  arizaSecimHaritasiniKur();
}

// --- Canlı Filo ---
const HIZ_RENK_KOYU = { "#e34948": "#8f2c2c", "#eda100": "#8f6600", "#1baf7a": "#0f6b48" };

async function filoyuHaritayaCiz(harita, veri) {
  if (harita._filoKumesi) harita.removeLayer(harita._filoKumesi);
  const kume = L.markerClusterGroup({
    maxClusterRadius: 55,
    iconCreateFunction: (cluster) => {
      const cocuklar = cluster.getAllChildMarkers();
      const sayi = cocuklar.length;
      const ortHiz = cocuklar.reduce((s, m) => s + (m.aracHizi ?? 0), 0) / (sayi || 1);
      const renk = hizRengi(ortHiz);
      return L.divIcon({
        html: `<div style="background:${renk}dd;color:#fff;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;font-family:'IBM Plex Mono',monospace;border:2px solid ${HIZ_RENK_KOYU[renk]};">${sayi}</div>`,
        className: "",
        iconSize: [38, 38],
      });
    },
  });
  veri.forEach((a) => {
    const marker = L.marker([a.lat, a.lon], { icon: noktaIkonu(hizRengi(a.hiz), 4) })
      .bindPopup(`Plaka: ${a.plaka ?? "-"}<br>Kapı No: ${a.kapino ?? "-"}<br>Hız: ${a.hiz} km/h<br>Operatör: ${a.operator ?? "-"}`);
    marker.aracHizi = a.hiz;
    marker.addTo(kume);
  });
  harita.addLayer(kume);
  harita._filoKumesi = kume;
}

let filoHaritasi, filoVeriTumu = [];
const aktifOperatorler = new Set();
let esikDk = 15;

function operatorOzetTabloCiz(veri) {
  const gruplar = {};
  veri.forEach((a) => {
    gruplar[a.operator] ??= { sayi: 0, hizToplam: 0 };
    gruplar[a.operator].sayi++;
    gruplar[a.operator].hizToplam += a.hiz;
  });
  const satirlar = Object.entries(gruplar)
    .map(([op, g]) => ({ op, sayi: g.sayi, ortHiz: g.hizToplam / g.sayi }))
    .sort((a, b) => b.sayi - a.sayi);

  const tablo = document.getElementById("operator-ozet-tablo");
  tablo.querySelector("thead").innerHTML = "<tr><th>Operatör</th><th>Araç Sayısı</th><th>Ortalama Hız</th></tr>";
  tablo.querySelector("tbody").innerHTML = satirlar
    .map((s) => `<tr><td>${s.op ?? "-"}</td><td>${s.sayi}</td><td>${s.ortHiz.toFixed(1)} km/h</td></tr>`)
    .join("");
}

function filoUygula() {
  const filtreli = filoVeriTumu.filter((a) => a.dakika_once <= esikDk && aktifOperatorler.has(a.operator));
  document.getElementById("kpi-filo-sayisi").textContent = filtreli.length.toLocaleString("tr-TR");
  document.getElementById("kpi-filo-duruyor").textContent = filtreli.filter((a) => a.hiz < 5).length.toLocaleString("tr-TR");
  document.getElementById("kpi-filo-hareket").textContent = filtreli.filter((a) => a.hiz >= 5).length.toLocaleString("tr-TR");
  if (filoHaritasi) filoyuHaritayaCiz(filoHaritasi, filtreli);
  operatorOzetTabloCiz(filtreli);
}

async function filoYukle() {
  filoVeriTumu = await fetch(`${API}/api/filo`).then((r) => r.json());
  const operatorler = [...new Set(filoVeriTumu.map((a) => a.operator))].filter(Boolean).sort();
  operatorler.forEach((o) => aktifOperatorler.add(o));

  document.getElementById("operator-filtre").innerHTML = operatorler.map(
    (o) => `<button type="button" class="cip aktif" data-op="${o}">${o}</button>`
  ).join("");
  document.querySelectorAll("#operator-filtre .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      cip.classList.toggle("aktif");
      const o = cip.dataset.op;
      cip.classList.contains("aktif") ? aktifOperatorler.add(o) : aktifOperatorler.delete(o);
      filoUygula();
    });
  });

  document.getElementById("esik-dk-slider").addEventListener("input", (e) => {
    esikDk = Number(e.target.value);
    document.getElementById("esik-dk-deger").textContent = esikDk;
    filoUygula();
  });

  filoHaritasi = koyuHarita("filo-harita");
  filoUygula();

  const garajButon = document.getElementById("garaj-toggle");
  let garajKatmani = null;
  garajButon.addEventListener("click", async () => {
    const acik = garajButon.classList.toggle("aktif");
    if (acik) {
      if (!garajKatmani) {
        const garajlar = await fetch(`${API}/api/garajlar`).then((r) => r.json());
        garajKatmani = L.layerGroup(
          garajlar.map((g) =>
            L.marker([g.enlem, g.boylam], { icon: noktaIkonu("#8b5cf6", 7) }).bindPopup(g.GARAJ_ADI)
          )
        );
      }
      garajKatmani.addTo(filoHaritasi);
    } else if (garajKatmani) {
      filoHaritasi.removeLayer(garajKatmani);
    }
  });

  document.getElementById("filo-hat-arama").addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;
    const hatKodu = e.target.value.trim();
    if (!hatKodu) return;
    const sonucKutu = document.getElementById("filo-hat-sonuc");
    const kayitlar = await fetch(`${API}/api/filo/hat?hat_kodu=${encodeURIComponent(hatKodu)}`).then((r) => r.json());
    if (!kayitlar.length) { sonucKutu.innerHTML = `<p class="yukleniyor">Bu hat için şu an araç bulunamadı.</p>`; return; }
    sonucKutu.innerHTML = kayitlar.map(
      (k) => `<button type="button" class="arama-sonuc-satir" data-lat="${k.enlem}" data-lon="${k.boylam}">${k.kapino} · ${k.plaka ?? "plaka yok"} · durak: ${k.yakinDurakKodu}</button>`
    ).join("");
    sonucKutu.querySelectorAll(".arama-sonuc-satir").forEach((btn) => {
      btn.addEventListener("click", () => filoHaritasi.setView([Number(btn.dataset.lat), Number(btn.dataset.lon)], 16));
    });
  });

  document.getElementById("filo-plaka-arama").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const q = e.target.value.trim().replace(" ", "").toLowerCase();
    if (!q) return;
    const sonucKutu = document.getElementById("filo-plaka-sonuc");
    const eslesenler = filoVeriTumu.filter(
      (a) => String(a.plaka ?? "").replace(" ", "").toLowerCase().includes(q) || String(a.kapino ?? "").toLowerCase().includes(q)
    );
    if (!eslesenler.length) { sonucKutu.innerHTML = `<p class="yukleniyor">Eşleşen araç bulunamadı.</p>`; return; }
    sonucKutu.innerHTML = eslesenler.slice(0, 20).map(
      (a) => `<button type="button" class="arama-sonuc-satir" data-lat="${a.lat}" data-lon="${a.lon}">${a.plaka} · Kapı No: ${a.kapino} · ${a.operator}</button>`
    ).join("");
    sonucKutu.querySelectorAll(".arama-sonuc-satir").forEach((btn) => {
      btn.addEventListener("click", () => filoHaritasi.setView([Number(btn.dataset.lat), Number(btn.dataset.lon)], 16));
    });
  });

  setInterval(async () => {
    filoVeriTumu = await fetch(`${API}/api/filo`).then((r) => r.json());
    filoUygula();
  }, 60_000);
}

// --- Saatlik Yoğunluk ---
const GUN_SIRA = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const GUN_ETIKET = { Monday: "Pzt", Tuesday: "Sal", Wednesday: "Çar", Thursday: "Per", Friday: "Cum", Saturday: "Cmt", Sunday: "Paz" };
const aktifIlceler = new Set();
let yogunlukGrafikleri = {};

async function yogunlukVeriGetir() {
  const secili = [...aktifIlceler];
  const hat = document.getElementById("yogunluk-hat-arama").value.trim();
  const params = new URLSearchParams();
  if (secili.length && secili.length < document.querySelectorAll("#yogunluk-ilce-filtre .cip").length) {
    params.set("ilceler", secili.join(","));
  }
  if (hat) params.set("hat", hat);
  return fetch(`${API}/api/yogunluk?${params.toString()}`).then((r) => r.json());
}

async function yogunlukUygula() {
  const veri = await yogunlukVeriGetir();
  document.getElementById("kpi-yogunluk-toplam").textContent = veri.toplam_yolculuk.toLocaleString("tr-TR");

  Object.values(yogunlukGrafikleri).forEach((g) => g.destroy());
  yogunlukGrafikleri.saatlik = cizYogunlukGrafigi("yogunluk-grafik", veri.saatlik);

  const pivot = {};
  veri.isi.forEach((d) => { pivot[`${d.gun}_${d.saat}`] = d.ortalama_yolcu; });
  const saatler = [...Array(24).keys()];
  yogunlukGrafikleri.isi = new Chart(document.getElementById("yogunluk-isi-grafik"), {
    type: "bar",
    data: {
      labels: saatler,
      datasets: GUN_SIRA.map((g, i) => ({
        label: GUN_ETIKET[g],
        data: saatler.map((s) => pivot[`${g}_${s}`] ?? 0),
        backgroundColor: `hsl(${210 - i * 25},65%,${40 + i * 3}%)`,
      })),
    },
    options: { ...grafikSecenekleri(), scales: { ...grafikSecenekleri().scales, x: { ...grafikSecenekleri().scales.x, stacked: true }, y: { ...grafikSecenekleri().scales.y, stacked: true } } },
  });

  const ilceTablo = document.getElementById("yogunluk-ilce-tablo");
  ilceTablo.querySelector("thead").innerHTML = "<tr><th>İlçe</th><th>Toplam Yolcu</th></tr>";
  ilceTablo.querySelector("tbody").innerHTML = veri.ilce_ozet
    .map((r) => `<tr><td>${r.ilce}</td><td>${r.toplam_yolcu.toLocaleString("tr-TR")}</td></tr>`)
    .join("");
}

async function yogunlukYukle() {
  const ilkVeri = await yogunlukVeriGetir();
  ilkVeri.ilce_listesi.forEach((i) => aktifIlceler.add(i));
  document.getElementById("yogunluk-ilce-filtre").innerHTML = ilkVeri.ilce_listesi.map(
    (i) => `<button type="button" class="cip aktif" data-ilce="${i}">${i}</button>`
  ).join("");
  document.querySelectorAll("#yogunluk-ilce-filtre .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      cip.classList.toggle("aktif");
      const i = cip.dataset.ilce;
      cip.classList.contains("aktif") ? aktifIlceler.add(i) : aktifIlceler.delete(i);
      yogunlukUygula();
    });
  });
  document.getElementById("yogunluk-hat-arama").addEventListener("change", yogunlukUygula);
  await yogunlukUygula();

  const dun = dunTarihISO();
  const gunlukTarihGirdi = document.getElementById("gunluk-yolculuk-tarih");
  gunlukTarihGirdi.value = dun;
  gunlukTarihGirdi.max = dun;
  gunlukTarihGirdi.addEventListener("change", (e) => gunlukYolculukCiz(e.target.value));
  await gunlukYolculukCiz(dun);
}

let gunlukYolculukGrafik = null;

async function gunlukYolculukCiz(tarihISO) {
  const veri = await fetch(`${API}/api/gunluk-yolculuk?tarih=${tarihISO}`).then((r) => r.json());
  const sirali = [...veri].sort((a, b) => b.Yolculuk - a.Yolculuk).slice(0, 20);

  if (gunlukYolculukGrafik) gunlukYolculukGrafik.destroy();
  gunlukYolculukGrafik = new Chart(document.getElementById("gunluk-yolculuk-grafik"), {
    type: "bar",
    data: {
      labels: sirali.map((r) => r.Hat),
      datasets: [{ label: "Yolcu sayısı", data: sirali.map((r) => r.Yolculuk), backgroundColor: "#3987e5" }],
    },
    options: grafikSecenekleri(),
  });
}

// --- Duyurular ---
let duyuruVeriTumu = [];
const aktifDuyuruTipleri = new Set();

function duyuruUygula() {
  const arama = document.getElementById("duyuru-hat-arama").value.toLowerCase();
  const filtreli = duyuruVeriTumu.filter((d) => {
    if (!aktifDuyuruTipleri.has(d.TIP)) return false;
    if (arama && !String(d.HATKODU ?? "").toLowerCase().includes(arama) && !String(d.HAT ?? "").toLowerCase().includes(arama)) return false;
    return true;
  });

  const liste = document.getElementById("duyuru-liste");
  document.getElementById("kpi-duyuru-sayfa").textContent = filtreli.length;
  if (!filtreli.length) {
    liste.innerHTML = `<p class="yukleniyor">Bu filtrelerle eşleşen duyuru yok.</p>`;
    return;
  }
  liste.innerHTML = filtreli
    .map((d) => `
      <div class="duyuru-oge">
        <div class="hat">${d.TIP === "Sefer" ? "🛑" : "📢"} Hat ${d.HATKODU ?? "-"} — ${d.HAT ?? ""}</div>
        <div class="mesaj">${d.MESAJ ?? ""}</div>
        <div class="zaman">${d.GUNCELLEME_SAATI ?? ""}</div>
      </div>`)
    .join("");
}

async function duyurularYukle() {
  duyuruVeriTumu = await fetch(`${API}/api/duyurular`).then((r) => r.json());
  const tipler = [...new Set(duyuruVeriTumu.map((d) => d.TIP))];
  tipler.forEach((t) => aktifDuyuruTipleri.add(t));

  document.getElementById("duyuru-tip-filtre").innerHTML = tipler.map(
    (t) => `<button type="button" class="cip aktif" data-tip="${t}">${t}</button>`
  ).join("");
  document.querySelectorAll("#duyuru-tip-filtre .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      cip.classList.toggle("aktif");
      const t = cip.dataset.tip;
      cip.classList.contains("aktif") ? aktifDuyuruTipleri.add(t) : aktifDuyuruTipleri.delete(t);
      duyuruUygula();
    });
  });
  document.getElementById("duyuru-hat-arama").addEventListener("input", duyuruUygula);
  document.getElementById("duyuru-yenile-buton").addEventListener("click", async () => {
    duyuruVeriTumu = await fetch(`${API}/api/duyurular`).then((r) => r.json());
    duyuruUygula();
  });

  duyuruUygula();
}

// --- Kaza Haritası ---
let kazaHaritasi, kazaVeriTumu = [];

function kazaHaritayiCiz(gorunum) {
  if (kazaHaritasi._kume) kazaHaritasi.removeLayer(kazaHaritasi._kume);
  if (kazaHaritasi._isi) kazaHaritasi.removeLayer(kazaHaritasi._isi);

  if (gorunum === "isi") {
    kazaHaritasi._isi = L.heatLayer(kazaVeriTumu.map((k) => [k.ENLEM, k.BOYLAM]), ISI_HARITA_AYARLARI).addTo(kazaHaritasi);
    return;
  }
  const kume = L.markerClusterGroup({ maxClusterRadius: 40 });
  kazaVeriTumu.forEach((k) => {
    L.marker([k.ENLEM, k.BOYLAM], { icon: noktaIkonu("#e34948", 6) })
      .bindPopup(`Tarih/Saat: ${k.zaman}`)
      .addTo(kume);
  });
  kazaHaritasi.addLayer(kume);
  kazaHaritasi._kume = kume;
}

async function kazaYukle() {
  kazaVeriTumu = await fetch(`${API}/api/kaza`).then((r) => r.json());
  document.getElementById("kpi-kaza-toplam").textContent = kazaVeriTumu.length;
  kazaHaritasi = koyuHarita("kaza-harita");
  kazaHaritayiCiz("nokta");

  document.querySelectorAll("#kaza-gorunum-secim .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      document.querySelectorAll("#kaza-gorunum-secim .cip").forEach((c) => c.classList.remove("aktif"));
      cip.classList.add("aktif");
      kazaHaritayiCiz(cip.dataset.gorunum);
    });
  });
}

// --- Plana Uyum ---
let planauyumVeri = null, planauyumYon = "cok_geciken", planauyumGrafikleri = {};

function dunTarihISO() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function planauyumCiz() {
  if (!planauyumVeri || !planauyumVeri.gorevler.length) return;
  const veri = planauyumVeri;

  let hatOzet = [...veri.hat_ozet];
  let baslik, renk;
  if (planauyumYon === "en_dakik") {
    hatOzet.sort((a, b) => Math.abs(a.ortalama_gecikme_dk) - Math.abs(b.ortalama_gecikme_dk));
    baslik = "En Dakik (Plana En Yakın) 15 Hat"; renk = "#199e70";
  } else if (planauyumYon === "en_erken") {
    hatOzet.sort((a, b) => a.ortalama_gecikme_dk - b.ortalama_gecikme_dk);
    baslik = "En Erken Kalkan 15 Hat"; renk = "#3987e5";
  } else {
    hatOzet.sort((a, b) => b.ortalama_gecikme_dk - a.ortalama_gecikme_dk);
    baslik = "En Çok Geciken 15 Hat"; renk = "#d95926";
  }
  hatOzet = hatOzet.slice(0, 15);
  document.getElementById("planauyum-bar-baslik").textContent = baslik;

  const tumGecikmeler = veri.gorevler.map((g) => g.gecikme_dk);
  const ortalama = tumGecikmeler.reduce((s, g) => s + g, 0) / (tumGecikmeler.length || 1);
  const zamaninda = tumGecikmeler.filter((g) => Math.abs(g) <= 5).length;
  document.getElementById("kpi-planauyum-gecikme").textContent = `${ortalama.toFixed(1)} dk`;
  document.getElementById("kpi-planauyum-zamaninda").textContent = `%${(100 * zamaninda / (tumGecikmeler.length || 1)).toFixed(1)}`;

  if (planauyumGrafikleri.bar) planauyumGrafikleri.bar.destroy();
  planauyumGrafikleri.bar = new Chart(document.getElementById("planauyum-bar"), {
    type: "bar",
    data: {
      labels: hatOzet.map((h) => h.SHATKODU),
      datasets: [{ label: "Ortalama gecikme (dk)", data: hatOzet.map((h) => h.ortalama_gecikme_dk), backgroundColor: renk }],
    },
    options: grafikSecenekleri(),
  });

  if (!planauyumGrafikleri.hist) {
    const binSayisi = 40;
    const min = Math.min(...tumGecikmeler), max = Math.max(...tumGecikmeler);
    const genislik = (max - min) / binSayisi || 1;
    const binler = Array(binSayisi).fill(0);
    tumGecikmeler.forEach((g) => {
      const idx = Math.min(binSayisi - 1, Math.floor((g - min) / genislik));
      binler[idx]++;
    });
    planauyumGrafikleri.hist = new Chart(document.getElementById("planauyum-hist"), {
      type: "bar",
      data: {
        labels: binler.map((_, i) => (min + i * genislik).toFixed(0)),
        datasets: [{ label: "Görev sayısı", data: binler, backgroundColor: "#3987e5" }],
      },
      options: { ...grafikSecenekleri(), scales: { ...grafikSecenekleri().scales, x: { ...grafikSecenekleri().scales.x, ticks: { color: "#8b8d94", maxTicksLimit: 12 } } } },
    });
  }

  planauyumTabloCiz(veri.gorevler);
}

function planauyumTabloCiz(gorevler) {
  const arama = document.getElementById("planauyum-arama").value.toLowerCase();
  const filtreli = arama ? gorevler.filter((g) => String(g.SHATKODU).toLowerCase().includes(arama)) : gorevler;
  const tablo = document.getElementById("planauyum-tablo");
  tablo.querySelector("thead").innerHTML = "<tr><th>Hat</th><th>Kapı No</th><th>Gecikme (dk)</th></tr>";
  tablo.querySelector("tbody").innerHTML = filtreli
    .slice(0, 300)
    .map((g) => `<tr><td>${g.SHATKODU}</td><td>${g.SKAPINUMARA}</td><td>${g.gecikme_dk.toFixed(1)}</td></tr>`)
    .join("");
}

async function planlananGercekGoster(hat, tarihStr) {
  if (!hat) return;
  const gercekSayisi = planauyumVeri.gorevler.filter((g) => g.SHATKODU === hat).length;
  document.getElementById("kpi-gercek-sefer").textContent = gercekSayisi;
  document.getElementById("kpi-planlanan-sefer").textContent = "…";

  const barDolu = document.getElementById("oran-bar-dolu");
  const yuzdeMetin = document.getElementById("oran-yuzde-metin");
  const aciklamaMetin = document.getElementById("oran-aciklama-metin");
  yuzdeMetin.textContent = "…";
  aciklamaMetin.textContent = "";
  barDolu.style.width = "0%";

  const { planlanan } = await fetch(`${API}/api/planlanan-sefer?hat=${encodeURIComponent(hat)}&tarih=${tarihStr}`).then((r) => r.json());
  document.getElementById("kpi-planlanan-sefer").textContent = planlanan ?? "—";

  if (!planlanan) {
    yuzdeMetin.textContent = "—";
    aciklamaMetin.textContent = "Planlanan sefer verisi alınamadı.";
    return;
  }

  const oran = (100 * gercekSayisi) / planlanan;
  let renk = "#e34948";
  if (oran >= 95) renk = "#199e70";
  else if (oran >= 80) renk = "#c98500";

  yuzdeMetin.textContent = `%${oran.toFixed(0)}`;
  yuzdeMetin.style.color = renk;
  barDolu.style.width = `${Math.min(oran, 100)}%`;
  barDolu.style.background = renk;
  aciklamaMetin.textContent =
    oran >= 100
      ? `Planlanandan ${gercekSayisi - planlanan} sefer fazla yapılmış (${gercekSayisi} / ${planlanan}).`
      : `${planlanan - gercekSayisi} sefer eksik yapılmış (${gercekSayisi} / ${planlanan}).`;
}

function planlananHatSecimiKur(tarihStr) {
  const hatlar = [...new Set(planauyumVeri.gorevler.map((g) => g.SHATKODU))].sort();
  const secim = document.getElementById("planlanan-hat-secim");
  secim.innerHTML = hatlar.map((h) => `<option value="${h}">${h}</option>`).join("");
  secim.onchange = () => planlananGercekGoster(secim.value, tarihStr);
  if (hatlar.length) planlananGercekGoster(hatlar[0], tarihStr);
}

async function planauyumTariheGoreYukle(tarihISO) {
  document.getElementById("planauyum-tarih-rozet").textContent = `📅 ${tarihISO.split("-").reverse().join(".")}`;
  const tarihStr = tarihISO.replace(/-/g, "");
  planauyumVeri = await fetch(`${API}/api/planauyum?tarih=${tarihStr}`).then((r) => r.json());
  if (planauyumGrafikleri.hist) { planauyumGrafikleri.hist.destroy(); planauyumGrafikleri.hist = null; }
  if (!planauyumVeri.gorevler.length) {
    document.getElementById("kpi-planauyum-gecikme").textContent = "—";
    document.getElementById("kpi-planauyum-zamaninda").textContent = "—";
    return;
  }
  planauyumCiz();
  planlananHatSecimiKur(tarihStr);
}

async function planaUyumYukle() {
  const dun = dunTarihISO();
  document.getElementById("planauyum-tarih").value = dun;
  document.getElementById("planauyum-tarih").max = dun;

  document.getElementById("planauyum-tarih").addEventListener("change", (e) => planauyumTariheGoreYukle(e.target.value));
  document.querySelectorAll("#planauyum-gorunum .cip").forEach((cip) => {
    cip.addEventListener("click", () => {
      document.querySelectorAll("#planauyum-gorunum .cip").forEach((c) => c.classList.remove("aktif"));
      cip.classList.add("aktif");
      planauyumYon = cip.dataset.yon;
      planauyumCiz();
    });
  });
  document.getElementById("planauyum-arama").addEventListener("input", () => planauyumVeri && planauyumTabloCiz(planauyumVeri.gorevler));

  await planauyumTariheGoreYukle(dun);
}

// --- AI Asistan (ortak fonksiyon -- hem balon hem Genel Bakış'taki gömülü sohbet kullanıyor) ---
function sohbetSatiri(rol, icerikHtml, id) {
  const avatar = rol === "kullanici" ? "🧑" : "🤖";
  return `
    <div class="sohbet-satir ${rol}"${id ? ` id="${id}"` : ""}>
      <span class="sohbet-avatar">${avatar}</span>
      <div class="sohbet-icerik">${icerikHtml}</div>
    </div>`;
}

function kacir(metin) {
  const d = document.createElement("div");
  d.textContent = metin;
  return d.innerHTML;
}

// Her sohbet paneli (balon / Genel Bakış'taki gömülü) kendi geçmişini tutuyor --
// "o hat", "o araç" gibi önceki cevaba atıflı sorular çalışsın diye. Maliyet
// kontrolü için backend zaten son 6 mesajla sınırlıyor, burada da kırpıyoruz.
const sohbetGecmisleri = new Map();

async function sohbeteMesajGonder(mesaj, kapsayici) {
  if (!sohbetGecmisleri.has(kapsayici)) sohbetGecmisleri.set(kapsayici, []);
  const gecmis = sohbetGecmisleri.get(kapsayici);

  kapsayici.insertAdjacentHTML("beforeend", sohbetSatiri("kullanici", kacir(mesaj)));
  const yukleniyorId = `yukleniyor-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  kapsayici.insertAdjacentHTML("beforeend", sohbetSatiri("asistan", `<span class="dusunuyor">Düşünüyor…</span>`, yukleniyorId));
  kapsayici.scrollTop = kapsayici.scrollHeight;

  try {
    const { cevap, hat_kodu } = await fetch(`${API}/api/asistan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mesaj, gecmis: gecmis.slice(-6) }),
    }).then((r) => r.json());
    document.getElementById(yukleniyorId).outerHTML = sohbetSatiri("asistan", marked.parse(cevap));
    gecmis.push({ role: "user", content: mesaj }, { role: "assistant", content: cevap });

    if (hat_kodu) {
      await sekmeyeGec("verimlilik");
      guzergahYukle(hat_kodu);
    }
  } catch (err) {
    document.getElementById(yukleniyorId).outerHTML = sohbetSatiri("asistan", "Bağlantı hatası, backend çalışıyor mu?");
  }
  kapsayici.scrollTop = kapsayici.scrollHeight;
}

// --- Sağ alt balon ---
const sohbetPanel = document.getElementById("sohbet-panel");
const sohbetMesajlar = document.getElementById("sohbet-mesajlar");

document.getElementById("sohbet-acma-buton").addEventListener("click", () => sohbetPanel.classList.toggle("gizli"));
document.getElementById("sohbet-kapat-buton").addEventListener("click", () => sohbetPanel.classList.add("gizli"));

document.getElementById("sohbet-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const girdi = document.getElementById("sohbet-girdi");
  const mesaj = girdi.value.trim();
  if (!mesaj) return;
  girdi.value = "";
  await sohbeteMesajGonder(mesaj, sohbetMesajlar);
});

// --- Genel Bakış'ın altındaki gömülü sohbet + hazır sorular ---
const HAZIR_SORULAR = [
  "Şu an kaç otobüs var, kaçı hareket halinde?",
  "Aktif duyuru var mı?",
  "Kaç tane arıza bildirimi var?",
  "Şu an trafik nasıl?",
  "Son 14 günde kaç kaza olmuş?",
  "10A hattının verimlilik durumu nedir?",
  "14ŞB hattında kaç araç var?",
  "34 HO 1000 plakalı aracı bul",
  "14ŞB hattı için en yakın garaj neresi?",
  "132H hattının kalkış saatleri nedir?",
];

const anaSohbetMesajlar = document.getElementById("ana-sohbet-mesajlar");
document.getElementById("hazir-sorular-genel").innerHTML = HAZIR_SORULAR.map(
  (s) => `<button type="button" class="hazir-soru-btn">${s}</button>`
).join("");
document.querySelectorAll(".hazir-soru-btn").forEach((btn) => {
  btn.addEventListener("click", () => sohbeteMesajGonder(btn.textContent, anaSohbetMesajlar));
});

document.getElementById("ana-sohbet-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const girdi = document.getElementById("ana-sohbet-girdi");
  const mesaj = girdi.value.trim();
  if (!mesaj) return;
  girdi.value = "";
  await sohbeteMesajGonder(mesaj, anaSohbetMesajlar);
});

// --- Manuel arıza formu ---
let arizaSecimHaritasi, arizaSeciliMarker, arizaSeciliKonum = null;

function arizaSecimHaritasiniKur() {
  if (arizaSecimHaritasi) return;
  arizaSecimHaritasi = koyuHarita("ariza-secim-harita");
  arizaSecimHaritasi.on("click", (e) => {
    arizaSeciliKonum = [e.latlng.lat, e.latlng.lng];
    if (arizaSecimHaritasi._secimMarker) arizaSecimHaritasi.removeLayer(arizaSecimHaritasi._secimMarker);
    arizaSecimHaritasi._secimMarker = L.marker(arizaSeciliKonum, { icon: noktaIkonu("#3987e5", 8) }).addTo(arizaSecimHaritasi);
    document.getElementById("ariza-secili-konum").textContent = `Seçili konum: ${arizaSeciliKonum[0].toFixed(6)}, ${arizaSeciliKonum[1].toFixed(6)}`;
  });
  arizaSecimHaritasi.on("contextmenu", (e) => {
    if (e.originalEvent) e.originalEvent.preventDefault();
    if (arizaSecimHaritasi._secimMarker) {
      arizaSecimHaritasi.removeLayer(arizaSecimHaritasi._secimMarker);
      arizaSecimHaritasi._secimMarker = null;
    }
    arizaSeciliKonum = null;
    document.getElementById("ariza-secili-konum").textContent = "Henüz konum seçilmedi.";
  });
}

document.getElementById("manuel-ariza-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const mesaj = document.getElementById("manuel-mesaj").value.trim();
  if (!mesaj) { alert("Mesaj boş olamaz."); return; }
  if (!arizaSeciliKonum) { alert("Önce haritadan bir konum seç."); return; }

  await fetch(`${API}/api/ariza/manuel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      enlem: arizaSeciliKonum[0],
      boylam: arizaSeciliKonum[1],
      mesaj,
      kapino: document.getElementById("manuel-kapino").value.trim(),
      sicil: document.getElementById("manuel-sicil").value.trim(),
    }),
  });

  document.getElementById("manuel-ariza-form").reset();
  arizaSeciliKonum = null;
  if (arizaSecimHaritasi._secimMarker) arizaSecimHaritasi.removeLayer(arizaSecimHaritasi._secimMarker);
  document.getElementById("ariza-secili-konum").textContent = "Bildirim kaydedildi.";

  await arizaYukle();
});

// --- Üst bar genel arama: hat kodu / adı VEYA plaka / kapı no ---
function sekmeyeGec(hedef) {
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("aktif", b.dataset.section === hedef));
  document.querySelectorAll(".sayfa").forEach((s) => s.classList.toggle("aktif", s.id === `sayfa-${hedef}`));
  if (!yuklenenSekmeler.has(hedef)) {
    yuklenenSekmeler.add(hedef);
    return YUKLEYICILER[hedef]?.();
  }
  return Promise.resolve();
}

document.getElementById("genel-arama").addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim();
  if (!q) return;
  const qTemiz = q.replace(" ", "").toLowerCase();

  const hatVerisi = verimlilikVeri.length ? verimlilikVeri : await fetch(`${API}/api/verimlilik`).then((r) => r.json());
  const hatEslesme = hatVerisi.find((h) => String(h.hat_kodu).toLowerCase() === qTemiz || String(h.SHATADI).toLowerCase().includes(qTemiz));
  if (hatEslesme) {
    await sekmeyeGec("verimlilik");
    document.getElementById("verimlilik-arama").value = q;
    verimlilikTabloCiz(hatVerisi.filter((h) => String(h.hat_kodu).toLowerCase().includes(qTemiz) || String(h.SHATADI).toLowerCase().includes(qTemiz)));
    return;
  }

  const filoVerisi = await fetch(`${API}/api/filo`).then((r) => r.json());
  const aracEslesme = filoVerisi.find(
    (a) => String(a.plaka ?? "").replace(" ", "").toLowerCase().includes(qTemiz) || String(a.kapino ?? "").toLowerCase().includes(qTemiz)
  );
  if (aracEslesme) {
    await sekmeyeGec("filo");
    alert(`Bulundu: Plaka ${aracEslesme.plaka ?? "-"}, Kapı No ${aracEslesme.kapino ?? "-"}, Hız ${aracEslesme.hiz} km/h — haritada ilgili noktaya yakınlaşabilirsin.`);
    return;
  }

  alert(`"${q}" ile eşleşen bir hat veya araç bulunamadı.`);
});

// İlk sekmeyi yükle
genelBakisYukle().catch((e) => console.error(e));
yuklenenSekmeler.add("genel");
