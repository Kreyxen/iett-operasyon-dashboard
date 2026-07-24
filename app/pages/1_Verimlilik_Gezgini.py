"""
M1: Verimlilik Gezgini

data/processed/hat_segmentleri.csv dosyasını okuyup gösterir. Bu dosya
iett/src/hat_skorlama.py ile üretilmiş, iki farklı ayda (Haziran/Aralık
2024) 0.960 korelasyonla doğrulanmış bir analizin çıktısı -- burada
sadece sonucu görselleştiriyoruz, yeniden hesaplamıyoruz.

verimlilik_tier : ortalama_oran (yolcu/km) çeyrekliklerine göre
    alt_ceyrek / orta_alt / orta_ust / ust_ceyrek
hat_tipi_ad     : HAT_UZUNLUGU + ortalama_sefer'e göre KMeans kümeleme,
    operasyonel profil (tali/orta/uzun/ana_arter) -- yargısız, "iyi/kötü" değil
supheli_kod_eslesmesi : True ise BELBİM/İETT kod eşleşme sorunu var,
    bu hattın verimlilik tier'ine güvenilmemeli
"""
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
VERI_YOLU = PROJE_KOKU / "data" / "processed" / "hat_segmentleri.csv"

st.set_page_config(page_title="Verimlilik Gezgini", layout="wide")
st.title("Verimlilik Gezgini — Hat Bazlı Performans")

if not VERI_YOLU.exists():
    st.error(f"Veri bulunamadı: {VERI_YOLU}")
    st.stop()

df = pd.read_csv(VERI_YOLU)

TIER_ETIKET = {
    "alt_ceyrek": "Alt Çeyrek",
    "orta_alt": "Orta Alt",
    "orta_ust": "Orta Üst",
    "ust_ceyrek": "Üst Çeyrek",
}
TIP_ETIKET = {
    "ana_arter": "Ana Arter",
    "orta_yogunluklu": "Orta Yoğunluklu",
    "tali_kucuk": "Tali Küçük",
    "uzun_kirsal": "Uzun Kırsal",
}

st.caption(
    "Verimlilik = yolcu / km oranı. Haziran ve Aralık 2024 verileriyle "
    "0.960 korelasyonla doğrulanmış bir metrik."
)

col1, col2, col3 = st.columns(3)
with col1:
    tier_secim = st.multiselect(
        "Verimlilik tier",
        options=sorted(df["verimlilik_tier"].unique()),
        default=sorted(df["verimlilik_tier"].unique()),
        format_func=lambda x: TIER_ETIKET.get(x, x),
    )
with col2:
    tip_secim = st.multiselect(
        "Hat tipi",
        options=sorted(df["hat_tipi_ad"].unique()),
        default=sorted(df["hat_tipi_ad"].unique()),
        format_func=lambda x: TIP_ETIKET.get(x, x),
    )
with col3:
    supheli_haric = st.checkbox("Şüpheli kod eşleşmelerini gizle", value=True)

filtreli = df[df["verimlilik_tier"].isin(tier_secim) & df["hat_tipi_ad"].isin(tip_secim)]
if supheli_haric:
    filtreli = filtreli[~filtreli["supheli_kod_eslesmesi"]]

st.metric("Gösterilen hat sayısı", len(filtreli))

filtreli = filtreli.copy()
filtreli["hat_tipi_g"] = filtreli["hat_tipi_ad"].map(TIP_ETIKET)
filtreli["verimlilik_tier_g"] = filtreli["verimlilik_tier"].map(TIER_ETIKET)

RENK_HARITASI = {
    TIP_ETIKET["ana_arter"]: "#3987e5",       # mavi
    TIP_ETIKET["orta_yogunluklu"]: "#d95926",  # turuncu
    TIP_ETIKET["tali_kucuk"]: "#199e70",       # aqua
    TIP_ETIKET["uzun_kirsal"]: "#c98500",      # sarı
}

fig = px.scatter(
    filtreli,
    x="HAT_UZUNLUGU",
    y="ortalama_oran",
    color="hat_tipi_g",
    color_discrete_map=RENK_HARITASI,
    hover_name="SHATADI",
    hover_data=["hat_kodu", "verimlilik_tier", "ortalama_sefer"],
    labels={
        "HAT_UZUNLUGU": "Hat uzunluğu (km)",
        "ortalama_oran": "Ortalama yolcu/km oranı",
        "hat_tipi_g": "Hat tipi",
    },
    title="Hat uzunluğu vs. verimlilik oranı",
    template="plotly_dark",
)
fig.update_traces(marker=dict(size=7, opacity=0.6, line=dict(width=0.5, color="#1a1a19")))
fig.update_layout(
    height=750,
    plot_bgcolor="#1a1a19",
    paper_bgcolor="#1a1a19",
    font=dict(color="#c3c2b7"),
    title_font=dict(color="#ffffff", size=18),
    legend_title_text="Hat tipi",
    xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
    yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
)
st.plotly_chart(fig, use_container_width=True)

DARK_LAYOUT = dict(
    plot_bgcolor="#1a1a19",
    paper_bgcolor="#1a1a19",
    font=dict(color="#c3c2b7"),
    title_font=dict(color="#ffffff", size=18),
    xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
    yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
)

col_bar, col_box = st.columns(2)

with col_bar:
    TIER_SIRA = [TIER_ETIKET[k] for k in ["alt_ceyrek", "orta_alt", "orta_ust", "ust_ceyrek"]]
    tier_sayim = filtreli["verimlilik_tier_g"].value_counts().reindex(TIER_SIRA).reset_index()
    tier_sayim.columns = ["verimlilik_tier_g", "hat_sayisi"]

    fig_bar = px.bar(
        tier_sayim,
        x="verimlilik_tier_g",
        y="hat_sayisi",
        color="verimlilik_tier_g",
        color_discrete_sequence=["#3987e5", "#199e70", "#d95926", "#c98500"],
        labels={"verimlilik_tier_g": "Verimlilik tier", "hat_sayisi": "Hat sayısı"},
        title="Tier'e göre hat dağılımı",
        template="plotly_dark",
    )
    fig_bar.update_layout(showlegend=False, **DARK_LAYOUT)
    st.plotly_chart(fig_bar, use_container_width=True)

with col_box:
    fig_box = px.box(
        filtreli,
        x="hat_tipi_g",
        y="ortalama_oran",
        color="hat_tipi_g",
        color_discrete_map=RENK_HARITASI,
        labels={"hat_tipi_g": "Hat tipi", "ortalama_oran": "Ortalama yolcu/km oranı"},
        title="Hat tipine göre oran dağılımı",
        template="plotly_dark",
    )
    fig_box.update_layout(showlegend=False, **DARK_LAYOUT)
    st.plotly_chart(fig_box, use_container_width=True)

st.subheader("Hat listesi")
arama = st.text_input("Hat kodu veya adında ara")
gosterilecek = filtreli
if arama:
    maske = (
        gosterilecek["hat_kodu"].astype(str).str.contains(arama, case=False, na=False)
        | gosterilecek["SHATADI"].str.contains(arama, case=False, na=False)
    )
    gosterilecek = gosterilecek[maske]

st.dataframe(
    gosterilecek[
        [
            "hat_kodu", "SHATADI", "verimlilik_tier", "hat_tipi_ad",
            "ortalama_oran", "ortalama_sefer", "ortalama_yolcu", "supheli_kod_eslesmesi",
        ]
    ],
    use_container_width=True,
)

st.subheader("Güzergah Haritası")

GUZERGAH_YOLU = PROJE_KOKU / "data" / "processed" / "iett_guzergah.csv"

if not GUZERGAH_YOLU.exists():
    st.info("Güzergah verisi bulunamadı.")
else:
    guzergah_df = pd.read_csv(GUZERGAH_YOLU)
    hat_secimi = st.selectbox(
        "Bir hat seç (güzergahını haritada gör)",
        options=sorted(filtreli["hat_kodu"].astype(str).unique()),
    )
    hat_guzergah = guzergah_df[guzergah_df["HATKODU"].astype(str) == hat_secimi].sort_values(["YON", "SIRANO"])

    if hat_guzergah.empty:
        st.info("Bu hat için güzergah verisi bulunamadı (durak sırası eksik olabilir).")
    else:
        YON_RENK = {"G": "#3987e5", "D": "#eb6834"}  # Gidiş / Dönüş
        YON_ETIKET = {"G": "Gidiş", "D": "Dönüş"}

        col_panel, col_map = st.columns([1, 3])

        with col_panel:
            yon_secim = st.radio(
                "Yön",
                options=sorted(hat_guzergah["YON"].unique()),
                format_func=lambda x: YON_ETIKET.get(x, x),
                horizontal=True,
            )
            secili_yon = hat_guzergah[hat_guzergah["YON"] == yon_secim].sort_values("SIRANO")

            st.markdown(f"**Kalkış:** {secili_yon.iloc[0]['DURAKADI']}")
            st.markdown(f"**Varış:** {secili_yon.iloc[-1]['DURAKADI']}")
            st.caption(f"{len(secili_yon)} durak — birini seç, harita yakınlaşsın")

            durak_listesi = list(secili_yon.itertuples(index=False))
            session_key = f"durak_secim_{hat_secimi}_{yon_secim}"
            if session_key not in st.session_state:
                st.session_state[session_key] = None

            with st.container(height=430):
                for i, durak in enumerate(durak_listesi):
                    if st.button(
                        f"{int(durak.SIRANO)}. {durak.DURAKADI}",
                        key=f"durak_btn_{hat_secimi}_{yon_secim}_{i}",
                        use_container_width=True,
                    ):
                        st.session_state[session_key] = i

            secim_index = st.session_state[session_key]
            if secim_index is not None:
                st.success(f"Seçili durak: {durak_listesi[secim_index].DURAKADI}")

            # --- Arıza kesişimi: bu güzergahın yakınında aktif bildirim var mı? ---
            ARIZA_DOSYALARI = ["bozuk_satih_islenmis.csv", "bozuk_satih_sentetik.csv", "bozuk_satih_manuel.csv"]
            ariza_parcalari = []
            for dosya_adi in ARIZA_DOSYALARI:
                yol = PROJE_KOKU / "data" / "processed" / dosya_adi
                if yol.exists():
                    ariza_parcalari.append(pd.read_csv(yol))
            ariza_df = pd.concat(ariza_parcalari, ignore_index=True) if ariza_parcalari else pd.DataFrame()

            yakin_ariza = pd.DataFrame()
            if not ariza_df.empty:
                # Aynı ~150m eşiğini DBSCAN'da (temizle_bozuk_satih.py) kullanmıştık,
                # tutarlılık için burada da aynı kabaca "1 derece ~ 100km" çevrimini
                # kullanıyoruz. Her arıza noktası için güzergahtaki EN YAKIN durağa
                # olan mesafeyi hesaplayıp eşiğin altındakileri "bu hatta" sayıyoruz.
                ESIK_DERECE = 150 / 100_000
                durak_koord = secili_yon[["enlem", "boylam"]].to_numpy()
                ariza_koord = ariza_df[["NENLEM", "NBOYLAM"]].to_numpy()
                farklar = ariza_koord[:, None, :] - durak_koord[None, :, :]
                mesafeler = (farklar ** 2).sum(axis=2) ** 0.5
                en_yakin_mesafe = mesafeler.min(axis=1)
                yakin_ariza = ariza_df[en_yakin_mesafe <= ESIK_DERECE]

            # --- Kaza kesişimi: bu güzergahın yakınında son 14 günde kaza olmuş mu? ---
            KAZA_YOLU = PROJE_KOKU / "data" / "processed" / "kaza_islenmis.csv"
            yakin_kaza = pd.DataFrame()
            if KAZA_YOLU.exists():
                kaza_df = pd.read_csv(KAZA_YOLU)
                if not kaza_df.empty:
                    kaza_koord = kaza_df[["ENLEM", "BOYLAM"]].to_numpy()
                    farklar_k = kaza_koord[:, None, :] - durak_koord[None, :, :]
                    mesafeler_k = (farklar_k ** 2).sum(axis=2) ** 0.5
                    en_yakin_mesafe_k = mesafeler_k.min(axis=1)
                    yakin_kaza = kaza_df[en_yakin_mesafe_k <= ESIK_DERECE]

            if not yakin_kaza.empty:
                st.error(f"🚨 Bu güzergahın ~150m yakınında son 14 günde **{len(yakin_kaza)}** kaza kaydı var.")

            if not yakin_ariza.empty:
                st.warning(f"⚠️ Bu güzergahın ~150m yakınında **{len(yakin_ariza)}** aktif arıza bildirimi var.")
            else:
                st.caption("Bu güzergahın yakınında aktif arıza bildirimi yok.")

        with col_map:
            if secim_index is not None:
                secili_durak = durak_listesi[secim_index]
                merkez = [secili_durak.enlem, secili_durak.boylam]
                zoom = 16
            else:
                merkez = [secili_yon["enlem"].mean(), secili_yon["boylam"].mean()]
                zoom = 12
            harita_g = folium.Map(location=merkez, zoom_start=zoom, tiles="cartodbpositron")

            renk = YON_RENK.get(yon_secim, "#199e70")
            koordinatlar = secili_yon[["enlem", "boylam"]].values.tolist()
            folium.PolyLine(
                koordinatlar, color=renk, weight=4, opacity=0.9,
                tooltip=YON_ETIKET.get(yon_secim, yon_secim),
            ).add_to(harita_g)
            for _, durak in secili_yon.iterrows():
                secili_mi = (
                    secim_index is not None
                    and durak["enlem"] == secili_durak.enlem
                    and durak["boylam"] == secili_durak.boylam
                )
                folium.CircleMarker(
                    location=[durak["enlem"], durak["boylam"]],
                    radius=9 if secili_mi else 3,
                    color="#e34948" if secili_mi else "#52514e",
                    fill=True,
                    fill_color="#e34948" if secili_mi else "#fcfcfb",
                    fill_opacity=1.0 if secili_mi else 0.9,
                    popup=durak["DURAKADI"],
                ).add_to(harita_g)

            for _, arz in yakin_ariza.iterrows():
                folium.Marker(
                    location=[arz["NENLEM"], arz["NBOYLAM"]],
                    icon=folium.Icon(color="orange", icon="warning-sign"),
                    popup=f"{arz['SMESAJMETNI']}<br>Kaynak: {arz['kaynak']}<br>{arz['zaman']}",
                ).add_to(harita_g)

            for _, kz in yakin_kaza.iterrows():
                folium.Marker(
                    location=[kz["ENLEM"], kz["BOYLAM"]],
                    icon=folium.Icon(color="darkred", icon="remove-sign"),
                    popup=f"Kaza — {kz['zaman']}",
                ).add_to(harita_g)

            st_folium(
                harita_g, height=500, width=None, use_container_width=True,
                key="guzergah_harita", returned_objects=[],
            )
            emoji = "🔵" if yon_secim == "G" else "🟠"
            st.caption(f"{emoji} {YON_ETIKET.get(yon_secim, yon_secim)} yönü gösteriliyor")
