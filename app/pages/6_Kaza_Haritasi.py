"""
Kaza Haritası (GetKazaLokasyon_json)

Mimari ilke (CLAUDE.md): sayfa veri çekmiyor, src/cek_kaza.py +
src/temizle_kaza.py tarafından üretilmiş data/processed/kaza_islenmis.csv
dosyasını okuyor. Veriyi güncellemek için:
    python src/cek_kaza.py
    python src/temizle_kaza.py

DİKKAT: Bu servis sadece kaza SAATİ ve KOORDİNATINI veriyor -- hangi
hatta, hangi araçta olduğu bilgisi YOK (İETT'nin kendi dokümanında
"Tur" alanı bile pratikte boş geliyor).
"""
import sys
from pathlib import Path

import folium
from folium.plugins import HeatMap
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
from tema import uygula as tema_uygula  # noqa: E402

VERI_YOLU = PROJE_KOKU / "data" / "processed" / "kaza_islenmis.csv"

st.set_page_config(page_title="Kaza Haritası", layout="wide")
tema_uygula()
st.title("Kaza Haritası")
st.caption(
    "Bu servis sadece kaza saati + koordinat veriyor; hangi hat/araç olduğu bilgisi yok. "
    "Veri, script'in çalıştırıldığı son 14 günü kapsıyor."
)

if not VERI_YOLU.exists():
    st.error(
        "İşlenmiş veri bulunamadı. Terminalde şu iki komutu sırayla çalıştır:\n\n"
        "```\npython src/cek_kaza.py\npython src/temizle_kaza.py\n```"
    )
    st.stop()

df = pd.read_csv(VERI_YOLU, parse_dates=["zaman"])

if df.empty:
    st.info("Şu an gösterilecek kaza kaydı yok.")
    st.stop()

st.metric("Toplam kaza kaydı", len(df))

gorunum = st.radio("Görünüm", ["Tıklanabilir noktalar", "Isı haritası"], horizontal=True)

merkez_enlem = df["ENLEM"].mean()
merkez_boylam = df["BOYLAM"].mean()
harita = folium.Map(location=[merkez_enlem, merkez_boylam], zoom_start=11, tiles="cartodbpositron")

if gorunum == "Tıklanabilir noktalar":
    for _, satir in df.iterrows():
        folium.CircleMarker(
            location=[satir["ENLEM"], satir["BOYLAM"]],
            radius=6,
            color="#e34948",
            fill=True,
            fill_opacity=0.85,
            popup=f"Tarih/Saat: {satir['zaman']}",
        ).add_to(harita)
else:
    HeatMap(
        df[["ENLEM", "BOYLAM"]].values.tolist(),
        radius=30,
        blur=25,
        min_opacity=0.45,
        gradient={0.2: "#3987e5", 0.4: "#199e70", 0.6: "#eda100", 0.8: "#d95926", 1.0: "#e34948"},
    ).add_to(harita)

st_folium(harita, width=1200, height=600, returned_objects=[])

with st.expander("Ham tablo"):
    st.dataframe(df)
