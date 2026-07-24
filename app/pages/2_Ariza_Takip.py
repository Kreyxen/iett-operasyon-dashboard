"""
M2: Arıza Takip Ekranı (Bozuk Satıh Bildirimleri)

Mimari ilke (CLAUDE.md): sayfalar veri ÇEKMEZ. Üç ayrı kaynaktan
gelen, önceden hazırlanmış CSV'leri okuyup birleştiriyoruz:
  - data/processed/bozuk_satih_islenmis.csv   -> kaynak: Sistem (İETT), gerçek API verisi
  - data/processed/bozuk_satih_sentetik.csv   -> kaynak: Sentetik (Demo), GERÇEK DEĞİL
  - data/processed/bozuk_satih_manuel.csv     -> kaynak: Manuel Bildirim, bu sayfadaki formdan girilir
Her kaydın "kaynak" sütunu haritada/tabloda açıkça gösterilir --
gerçek veriyle demo/manuel veri asla etiketsiz karıştırılmaz.

Sistem verisini güncellemek için:
    python src/cek_bozuk_satih.py
    python src/temizle_bozuk_satih.py
"""
from pathlib import Path

import folium
from folium.plugins import HeatMap
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"
SISTEM_YOLU = PROCESSED_KLASOR / "bozuk_satih_islenmis.csv"
SENTETIK_YOLU = PROCESSED_KLASOR / "bozuk_satih_sentetik.csv"
MANUEL_YOLU = PROCESSED_KLASOR / "bozuk_satih_manuel.csv"

KAYNAK_RENK = {
    "Sistem (İETT)": "red",
    "Sentetik (Demo)": "gray",
    "Manuel Bildirim": "blue",
}

st.set_page_config(page_title="Arıza Takip", layout="wide")
st.title("Arıza Takip — Bozuk Satıh Bildirimleri")


def kaynaklari_yukle():
    parcalar = []
    if SISTEM_YOLU.exists():
        parcalar.append(pd.read_csv(SISTEM_YOLU, parse_dates=["zaman"]))
    if SENTETIK_YOLU.exists():
        parcalar.append(pd.read_csv(SENTETIK_YOLU, parse_dates=["zaman"]))
    if MANUEL_YOLU.exists():
        parcalar.append(pd.read_csv(MANUEL_YOLU, parse_dates=["zaman"]))
    if not parcalar:
        return pd.DataFrame()
    return pd.concat(parcalar, ignore_index=True)


df = kaynaklari_yukle()

if not SISTEM_YOLU.exists():
    st.warning(
        "Sistem verisi (gerçek API) bulunamadı. Terminalde şu iki komutu sırayla çalıştır:\n\n"
        "```\npython src/cek_bozuk_satih.py\npython src/temizle_bozuk_satih.py\n```"
    )

# --- Manuel bildirim formu ---
with st.expander("➕ Yeni bildirim ekle (manuel)"):
    st.caption("Bu formdan eklenen kayıtlar 'Manuel Bildirim' olarak etiketlenir, İETT sisteminden gelmez.")

    st.write("**1) Konum seç** — haritada bir yere tıkla:")
    if "secilen_konum" not in st.session_state:
        st.session_state["secilen_konum"] = None

    secim_haritasi = folium.Map(location=[41.0082, 28.9784], zoom_start=11, tiles="cartodbpositron")
    if st.session_state["secilen_konum"]:
        folium.Marker(
            st.session_state["secilen_konum"],
            icon=folium.Icon(color="blue", icon="map-pin"),
        ).add_to(secim_haritasi)

    tiklama = st_folium(
        secim_haritasi, height=350, width=None, use_container_width=True,
        key="konum_secici", returned_objects=["last_clicked"],
    )
    if tiklama and tiklama.get("last_clicked"):
        st.session_state["secilen_konum"] = [tiklama["last_clicked"]["lat"], tiklama["last_clicked"]["lng"]]

    if st.session_state["secilen_konum"]:
        st.success(
            f"Seçili konum: {st.session_state['secilen_konum'][0]:.6f}, "
            f"{st.session_state['secilen_konum'][1]:.6f}"
        )
    else:
        st.info("Henüz konum seçilmedi.")

    st.write("**2) Detayları gir:**")
    with st.form("manuel_bildirim_formu", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            girilen_kapino = st.text_input("Kapı No (biliyorsan)", value="")
        with col_f2:
            girilen_sicil = st.text_input("Şoför Sicil (biliyorsan)", value="")
        girilen_mesaj = st.text_area("Mesaj (örn. 'Bu alanda satıh bozuk')")
        gonder = st.form_submit_button("Bildirimi Kaydet")

        if gonder:
            if not girilen_mesaj.strip():
                st.error("Mesaj boş olamaz.")
            elif not st.session_state["secilen_konum"]:
                st.error("Önce haritadan bir konum seç.")
            else:
                enlem_sec, boylam_sec = st.session_state["secilen_konum"]
                yeni_kayit = pd.DataFrame([{
                    "NMESAJID": int(pd.Timestamp.now().timestamp()),
                    "SKAPINUMARASI": girilen_kapino or "BELİRTİLMEDİ",
                    "SSOFORSICILNO": girilen_sicil or "BELİRTİLMEDİ",
                    "SMESAJMETNI": girilen_mesaj.strip(),
                    "zaman": pd.Timestamp.now(),
                    "NBOYLAM": boylam_sec,
                    "NENLEM": enlem_sec,
                    "kume_id": -1,
                    "kaynak": "Manuel Bildirim",
                }])
                onceki = pd.read_csv(MANUEL_YOLU, parse_dates=["zaman"]) if MANUEL_YOLU.exists() else pd.DataFrame()
                pd.concat([onceki, yeni_kayit], ignore_index=True).to_csv(MANUEL_YOLU, index=False)
                st.session_state["secilen_konum"] = None
                st.success("Bildirim kaydedildi. Sayfa yenilenince haritada görünecek.")
                st.rerun()

if df.empty:
    st.info("Şu an gösterilecek bildirim yok.")
    st.stop()

# --- Kaynak filtresi ---
kaynaklar = sorted(df["kaynak"].unique())
secili_kaynaklar = st.multiselect("Kaynak", options=kaynaklar, default=kaynaklar)
df = df[df["kaynak"].isin(secili_kaynaklar)]

kume_sayisi = df.loc[df["kume_id"] != -1, "kume_id"].nunique() if "kume_id" in df else 0
col1, col2 = st.columns(2)
col1.metric("Toplam bildirim", len(df))
col2.metric("Sıcak bölge (küme)", kume_sayisi)
st.caption("🔴 Sistem (İETT) · ⚫ Sentetik (Demo) · 🔵 Manuel Bildirim")

gorunum = st.radio("Görünüm", ["Tıklanabilir noktalar", "Isı haritası"], horizontal=True)

merkez_enlem = df["NENLEM"].mean()
merkez_boylam = df["NBOYLAM"].mean()
harita = folium.Map(location=[merkez_enlem, merkez_boylam], zoom_start=11, tiles="cartodbpositron")

if gorunum == "Tıklanabilir noktalar":
    for _, satir in df.iterrows():
        renk = KAYNAK_RENK.get(satir["kaynak"], "gray")
        popup_metin = (
            f"<b>Kaynak:</b> {satir['kaynak']}<br>"
            f"<b>Kapı No:</b> {satir['SKAPINUMARASI']}<br>"
            f"<b>Tarih:</b> {satir['zaman']}<br>"
            f"<b>Mesaj:</b> {satir['SMESAJMETNI']}<br>"
            f"<b>Şoför Sicil:</b> {satir['SSOFORSICILNO']}"
        )
        folium.CircleMarker(
            location=[satir["NENLEM"], satir["NBOYLAM"]],
            radius=7,
            color=renk,
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(popup_metin, max_width=250),
        ).add_to(harita)
else:
    HeatMap(df[["NENLEM", "NBOYLAM"]].values.tolist()).add_to(harita)

st_folium(harita, width=1200, height=600, returned_objects=[])

with st.expander("Ham tablo"):
    st.dataframe(df)
