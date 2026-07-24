"""
M3 Ek: Canlı Duyurular

Mimari ilke (CLAUDE.md): sayfa doğrudan servisten değil,
src/duyurular.py'deki fonksiyonu (kısa süreli önbellekle) çağırıyor.
Bu veri gerçekten canlı olduğu için M2'deki gibi diske arşivlemiyoruz.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
from duyurular import duyurular  # noqa: E402
from tema import uygula as tema_uygula  # noqa: E402

st.set_page_config(page_title="Duyurular", layout="wide")
tema_uygula()
st.title("Canlı Duyurular — Sefer İptalleri ve Güzergah Değişiklikleri")


@st.cache_data(ttl=120)
def veriyi_getir():
    kayitlar = duyurular()
    return pd.DataFrame(kayitlar)


col_baslik, col_buton = st.columns([4, 1])
with col_buton:
    if st.button("Yenile"):
        veriyi_getir.clear()

try:
    df = veriyi_getir()
except Exception as e:
    st.error(f"Servisten veri alınamadı: {e}")
    st.stop()

if df.empty:
    st.info("Şu an aktif duyuru yok.")
    st.stop()

st.caption(f"{len(df)} aktif duyuru · önbellek en fazla 2 dakika eski olabilir.")

col_f1, col_f2 = st.columns(2)
with col_f1:
    tip_secim = st.multiselect("Duyuru tipi", options=sorted(df["TIP"].unique()), default=sorted(df["TIP"].unique()))
with col_f2:
    hat_arama = st.text_input("Hat kodu veya adı ara")

df_f = df[df["TIP"].isin(tip_secim)]
if hat_arama:
    df_f = df_f[
        df_f["HATKODU"].str.contains(hat_arama, case=False, na=False)
        | df_f["HAT"].str.contains(hat_arama, case=False, na=False)
    ]

st.metric("Gösterilen duyuru", len(df_f))

# "Kayit Saati: 16:07" gibi bir metin -- tarih YOK, sadece saat. Düz
# HH:MM sıralaması gece yarısını atlayan durumlarda yanılır (dünün
# 23:25'i, bugünün 07:39'undan büyük görünür ama aslında daha eski).
# Bu yüzden: saat şu andan BÜYÜKSE bu "gelecekte" demek, imkansız --
# o zaman dünden kalma olmalı, bir gün geriye alıyoruz.
simdi = datetime.now(ISTANBUL).replace(tzinfo=None)  # sunucu saat dilimi UTC olabilir, biz İETT gibi İstanbul saatini kullanıyoruz


def zamani_coz(saat_metni):
    eslesme = pd.Series([saat_metni]).str.extract(r"(\d{2}:\d{2})")[0][0]
    if pd.isna(eslesme):
        return pd.NaT
    saat = datetime.strptime(eslesme, "%H:%M").time()
    aday = datetime.combine(simdi.date(), saat)
    if aday > simdi:
        aday -= timedelta(days=1)
    return aday


df_f = df_f.copy()
df_f["_gercek_zaman"] = df_f["GUNCELLEME_SAATI"].apply(zamani_coz)

for _, satir in df_f.sort_values("_gercek_zaman", ascending=False, na_position="last").iterrows():
    etiket = "🛑 Sefer İptali" if satir["TIP"] == "Sefer" else "📢 Genel Duyuru"
    with st.container(border=True):
        st.markdown(f"**{etiket} — Hat {satir['HATKODU']}** ({satir['HAT']})")
        st.write(satir["MESAJ"])
        if pd.notna(satir["_gercek_zaman"]):
            st.caption(satir["_gercek_zaman"].strftime("%d.%m.%Y %H:%M"))
        else:
            st.caption(satir["GUNCELLEME_SAATI"])
