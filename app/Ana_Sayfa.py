"""
Ana Sayfa: her modülden anlık/güncel bir özet.

Mimari ilke (CLAUDE.md): burada da ağır işi src/ fonksiyonları yapıyor,
sayfa sadece çağırıp (kısa süreli önbellekle) gösteriyor.
"""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

ISTANBUL = ZoneInfo("Europe/Istanbul")

PROJE_KOKU = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
from filo_konum import filo_konumlari  # noqa: E402
from duyurular import duyurular  # noqa: E402
from asistan import soru_sor  # noqa: E402
from tema import uygula as tema_uygula  # noqa: E402

st.set_page_config(page_title="İETT Operasyon Dashboard", layout="wide")
tema_uygula()
st.title("İETT Operasyon Dashboard")
st.caption("Staj projesi — her modülden güncel bir özet. Detaylar için soldaki menüyü kullan.")

PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"


@st.cache_data(ttl=60)
def filo_ozet():
    try:
        return len(filo_konumlari())
    except Exception:
        return None


@st.cache_data(ttl=120)
def duyuru_ozet():
    try:
        return len(duyurular())
    except Exception:
        return None


col1, col2, col3, col4 = st.columns(4)

verimlilik_yolu = PROCESSED_KLASOR / "hat_segmentleri.csv"
if verimlilik_yolu.exists():
    col1.metric("Analiz Edilen Hat", len(pd.read_csv(verimlilik_yolu)))
else:
    col1.metric("Analiz Edilen Hat", "—")

ariza_toplam = 0
for dosya_adi in ["bozuk_satih_islenmis.csv", "bozuk_satih_sentetik.csv", "bozuk_satih_manuel.csv"]:
    yol = PROCESSED_KLASOR / dosya_adi
    if yol.exists():
        ariza_toplam += len(pd.read_csv(yol))
col2.metric("Arıza Bildirimi (toplam)", ariza_toplam)

filo_sayisi = filo_ozet()
col3.metric("Filodaki Araç (canlı)", filo_sayisi if filo_sayisi is not None else "—")

duyuru_sayisi = duyuru_ozet()
col4.metric("Aktif Duyuru (canlı)", duyuru_sayisi if duyuru_sayisi is not None else "—")

st.divider()

st.subheader("Modüller")
st.markdown(
    "- **Verimlilik Gezgini** — hat bazlı yolcu/km performansı, tier + kümeleme, güzergah haritası\n"
    "- **Arıza Takip** — bozuk satıh bildirimleri (sistem + manuel + demo), DBSCAN sıcak bölgeler\n"
    "- **Canlı Filo** — filodaki tüm araçların anlık konumu, hat/plaka arama, operatör özeti\n"
    "- **Saatlik Yoğunluk** — BELBİM yolcu verisiyle saatlik/günlük yoğunluk, gün x saat ısı haritası\n"
    "- **Duyurular** — hat bazlı sefer iptali ve güzergah değişikliği duyuruları, canlı"
)

st.divider()

st.subheader("🤖 AI Asistan")
st.caption("Claude, canlı filo/duyuru/arıza verilerine erişebiliyor -- soruna göre gerçek veriye bakıp cevap veriyor.")

if "sohbet_gecmisi" not in st.session_state:
    st.session_state["sohbet_gecmisi"] = []

HAZIR_SORULAR = [
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
]

st.caption("Hazır sorular:")
hazir_secim = None
SUTUN_SAYISI = 3
for baslangic in range(0, len(HAZIR_SORULAR), SUTUN_SAYISI):
    satir_sorulari = HAZIR_SORULAR[baslangic:baslangic + SUTUN_SAYISI]
    buton_kolonlari = st.columns(SUTUN_SAYISI)
    for kolon, soru in zip(buton_kolonlari, satir_sorulari):
        with kolon:
            if st.button(soru, use_container_width=True):
                hazir_secim = soru

for mesaj in st.session_state["sohbet_gecmisi"]:
    with st.chat_message(mesaj["rol"]):
        st.write(mesaj["icerik"])

yazilan_mesaj = st.chat_input("Bir şey sor...")
kullanici_mesaji = hazir_secim or yazilan_mesaj
if kullanici_mesaji:
    st.session_state["sohbet_gecmisi"].append({"rol": "user", "icerik": kullanici_mesaji})
    with st.chat_message("user"):
        st.write(kullanici_mesaji)

    with st.chat_message("assistant"):
        try:
            # Son birkaç turu (maliyet kontrolü için sınırlı) Claude formatına
            # çevirip geçmiş olarak veriyoruz -- "o hat", "o araç" gibi önceki
            # cevaba atıflı sorular çalışsın diye.
            onceki_gecmis = [
                {"role": m["rol"], "content": m["icerik"]}
                for m in st.session_state["sohbet_gecmisi"][:-1][-6:]
            ]
            cevap, _ = soru_sor(kullanici_mesaji, gecmis=onceki_gecmis)
            st.write(cevap)
        except Exception as e:
            cevap = None
            st.error(f"Claude'a ulaşılamadı: {e}")

    if cevap:
        st.session_state["sohbet_gecmisi"].append({"rol": "assistant", "icerik": cevap})

st.divider()

st.caption(f"Son güncelleme: {datetime.now(ISTANBUL).strftime('%d.%m.%Y %H:%M:%S')}")
