"""
Sohbet Geçmişi (Admin)

AI asistana sorulan soru/cevapları private GitHub deposundan
(iett-sohbet-loglari) okuyup gösterir. Şifreyle korunuyor ki
dashboard'u paylaştığın herkes bu sayfayı göremesin.
"""
import sys
from pathlib import Path

import streamlit as st

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
import github_log  # noqa: E402

st.set_page_config(page_title="Sohbet Geçmişi", layout="wide")
st.title("🔒 Sohbet Geçmişi (Admin)")

sifre = st.text_input("Şifre", type="password")
if sifre != st.secrets.get("ADMIN_SIFRE", ""):
    if sifre:
        st.error("Yanlış şifre.")
    st.stop()

try:
    icerik = github_log.oku()
except Exception as e:
    st.error(f"Log okunamadı: {e}")
    st.stop()

st.markdown(icerik)
