"""
Sohbet Geçmişi (Admin)

AI asistana sorulan tüm soru/cevapları gösterir -- src/asistan.py'deki
sohbeti_kaydet() fonksiyonu her cevaptan sonra bunu CSV'ye ekliyor.
Şifreyle korunuyor ki dashboard'u paylaştığın herkes bu sayfayı göremesin.

NOT: Streamlit Cloud'un dosya sistemi kalıcı değil -- her yeni push/deploy
sonrası bu geçmiş sıfırlanır. Kısa süreli paylaşım için yeterli.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
LOG_YOLU = PROJE_KOKU / "data" / "processed" / "sohbet_gecmisi.csv"

st.set_page_config(page_title="Sohbet Geçmişi", layout="wide")
st.title("🔒 Sohbet Geçmişi (Admin)")

sifre = st.text_input("Şifre", type="password")
if sifre != st.secrets.get("ADMIN_SIFRE", ""):
    if sifre:
        st.error("Yanlış şifre.")
    st.stop()

if not LOG_YOLU.exists():
    st.info("Henüz hiç soru sorulmamış.")
    st.stop()

df = pd.read_csv(LOG_YOLU, parse_dates=["zaman"])
st.metric("Toplam soru", len(df))

for _, satir in df.sort_values("zaman", ascending=False).iterrows():
    with st.container(border=True):
        st.caption(str(satir["zaman"]))
        st.markdown(f"**Soru:** {satir['soru']}")
        st.write(f"**Cevap:** {satir['cevap']}")
