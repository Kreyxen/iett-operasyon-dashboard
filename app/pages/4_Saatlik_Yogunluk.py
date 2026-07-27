"""
M4: Saatlik Yoğunluk

Mimari ilke (CLAUDE.md): sayfa ham dosyayı işlemiyor, src/saatlik_yogunluk.py
'daki veri_yukle() fonksiyonunu çağırıyor (559 bin satır olduğu için
st.cache_data ile önbelleklenir, her etkileşimde diskten tekrar okunmaz).
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
from saatlik_yogunluk import veri_yukle  # noqa: E402
from trafik_indeksi import trafik_gecmisi  # noqa: E402
from gunluk_yolculuk import gunluk_hat_yolculuk  # noqa: E402
from tema import uygula as tema_uygula  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

ISTANBUL = ZoneInfo("Europe/Istanbul")

st.set_page_config(page_title="Saatlik Yoğunluk", layout="wide")
tema_uygula()
st.title("Saatlik Yoğunluk — BELBİM Yolcu Verisi (Haziran 2024)")


@st.cache_data
def yukle():
    return veri_yukle()

try:
    df = yukle()
except FileNotFoundError:
    st.error("data/raw/belbim_ozet_202406.parquet bulunamadı.")
    st.stop()

ilceler = sorted(df["town"].dropna().unique())
secili_ilceler = st.multiselect("İlçe", options=ilceler, default=ilceler)
df_f = df[df["town"].isin(secili_ilceler)]

hat_arama = st.text_input("Hat adı ara (opsiyonel, boş bırakırsan tüm hatlar)")
if hat_arama:
    df_f = df_f[df_f["line_name"].str.contains(hat_arama, case=False, na=False)]

if df_f.empty:
    st.warning("Bu filtrelerle eşleşen veri yok.")
    st.stop()

st.metric("Toplam yolculuk (filtrelenmiş)", f"{df_f['number_of_passenger'].sum():,}".replace(",", "."))

st.subheader("Saatlik Ortalama Yolcu — Hafta İçi vs Hafta Sonu")
st.caption(
    "Her saat için, o saatteki toplam yolcuyu kaç farklı güne bölündüğünü hesaplayıp "
    "'tipik bir günde bu saatte kaç yolcu' sorusuna cevap veriyoruz."
)

saatlik = (
    df_f.groupby(["transition_hour", "gun_tipi"])
    .agg(toplam_yolcu=("number_of_passenger", "sum"), gun_sayisi=("transition_date", "nunique"))
    .reset_index()
)
saatlik["ortalama_yolcu"] = saatlik["toplam_yolcu"] / saatlik["gun_sayisi"]

RENK_HARITASI = {"Hafta İçi": "#3987e5", "Hafta Sonu": "#d95926"}

fig = px.line(
    saatlik.sort_values("transition_hour"),
    x="transition_hour",
    y="ortalama_yolcu",
    color="gun_tipi",
    color_discrete_map=RENK_HARITASI,
    markers=True,
    labels={
        "transition_hour": "Saat",
        "ortalama_yolcu": "Ortalama yolcu (tipik gün)",
        "gun_tipi": "Gün tipi",
    },
    title="Saatlik ortalama yolcu yoğunluğu",
    template="plotly_dark",
)
fig.update_layout(
    height=500,
    plot_bgcolor="#1a1a19",
    paper_bgcolor="#1a1a19",
    font=dict(color="#c3c2b7"),
    title_font=dict(color="#ffffff", size=18),
    xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835", dtick=1),
    yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Isı Haritası — Gün x Saat")
GUN_SIRA = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
GUN_ETIKET = {
    "Monday": "Pzt", "Tuesday": "Sal", "Wednesday": "Çar", "Thursday": "Per",
    "Friday": "Cum", "Saturday": "Cmt", "Sunday": "Paz",
}

isi = (
    df_f.groupby(["haftanin_gunu", "transition_hour"])["number_of_passenger"]
    .mean()
    .reset_index()
)
isi["gun_g"] = isi["haftanin_gunu"].map(GUN_ETIKET)
pivot = isi.pivot(index="gun_g", columns="transition_hour", values="number_of_passenger")
pivot = pivot.reindex([GUN_ETIKET[g] for g in GUN_SIRA])

fig_isi = px.imshow(
    pivot,
    color_continuous_scale="Blues",
    labels={"x": "Saat", "y": "Gün", "color": "Ort. yolcu"},
    title="Gün x saat bazlı ortalama yolcu yoğunluğu",
    template="plotly_dark",
    aspect="auto",
)
fig_isi.update_layout(
    height=400,
    plot_bgcolor="#1a1a19",
    paper_bgcolor="#1a1a19",
    font=dict(color="#c3c2b7"),
    title_font=dict(color="#ffffff", size=18),
)
st.plotly_chart(fig_isi, use_container_width=True)

st.subheader("İlçe Bazlı Toplam Yolcu")
ilce_ozet = (
    df_f.groupby("town")["number_of_passenger"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={"town": "İlçe", "number_of_passenger": "Toplam Yolcu"})
)
st.dataframe(ilce_ozet, use_container_width=True)

st.divider()
st.subheader("Günün En Çok Yolculuk Yapan Hatları (Canlı)")
st.caption(
    "Yukarıdaki BELBİM verisinden farklı bir kaynak (GetIettYolculukHat_json) -- "
    "istediğin güne canlı sorgu atıp o günün gerçek yolcu sayılarını çekiyor. "
    "En çok yolculuk yapan 50 hattı döndürüyor. Bugünün verisi gün bitmeden "
    "genelde eksik geldiği için varsayılan olarak dünü öneriyoruz."
)

secili_gun = st.date_input(
    "Hangi günün verisine bakalım?",
    value=datetime.now(ISTANBUL).date() - timedelta(days=1),
    max_value=datetime.now(ISTANBUL).date(),
    key="yolculuk_hat_tarih",
)


@st.cache_data(ttl=3600)
def yolculuk_hat_yukle(tarih_str):
    return pd.DataFrame(gunluk_hat_yolculuk(tarih_str))


try:
    yolculuk_hat_df = yolculuk_hat_yukle(secili_gun.strftime("%Y-%m-%d"))
    yolculuk_hat_df = yolculuk_hat_df[yolculuk_hat_df["Hat"].notna()].sort_values("Yolculuk", ascending=False)

    if yolculuk_hat_df.empty:
        st.info("Bu gün için henüz veri yok (gün bitmeden veri gelmeyebilir, bir önceki günü dene).")
    else:
        st.metric("Toplam yolculuk (üst 50 hat)", f"{yolculuk_hat_df['Yolculuk'].sum():,}".replace(",", "."))

        fig_yolculuk_hat = px.bar(
            yolculuk_hat_df.head(20),
            x="Hat",
            y="Yolculuk",
            labels={"Hat": "Hat", "Yolculuk": "Yolcu Sayısı"},
            title=f"{secili_gun.strftime('%d.%m.%Y')} -- en çok yolculuk yapan 20 hat",
            template="plotly_dark",
            color_discrete_sequence=["#3987e5"],
        )
        fig_yolculuk_hat.update_layout(
            height=450,
            plot_bgcolor="#1a1a19",
            paper_bgcolor="#1a1a19",
            font=dict(color="#c3c2b7"),
            title_font=dict(color="#ffffff", size=18),
            xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
            yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
        )
        st.plotly_chart(fig_yolculuk_hat, use_container_width=True)

        with st.expander("Tüm 50 hat (ham tablo)"):
            st.dataframe(yolculuk_hat_df[["Hat", "Yolculuk"]], use_container_width=True)
except Exception as e:
    st.error(f"Servisten veri alınamadı: {e}")

st.divider()
st.subheader("Şehir Geneli Trafik Yoğunluğu (Canlı Trafik İndeksi)")
st.caption(
    "Bu, hat/yolcu verisinden farklı bir kaynak (İBB'nin canlı REST API'si) -- "
    "toplu taşıma yoğunluğunu değil, şehir genelindeki araç trafiğini gösterir. Gerçekten canlı, saatlik güncelleniyor."
)


@st.cache_data(ttl=300)
def trafik_yukle(gun):
    return pd.DataFrame(trafik_gecmisi(gun=gun, periyot="H"))


gun_sayisi = st.slider("Kaç günlük trend gösterilsin?", min_value=1, max_value=14, value=3)
try:
    trafik_df = trafik_yukle(gun_sayisi)
    trafik_df["TrafficIndexDate"] = pd.to_datetime(trafik_df["TrafficIndexDate"])

    fig_trafik = px.line(
        trafik_df.sort_values("TrafficIndexDate"),
        x="TrafficIndexDate",
        y="TrafficIndex",
        labels={"TrafficIndexDate": "Tarih/Saat", "TrafficIndex": "Trafik İndeksi (0-99)"},
        title=f"Son {gun_sayisi} günde saatlik trafik indeksi",
        template="plotly_dark",
        color_discrete_sequence=["#3987e5"],
    )
    fig_trafik.update_traces(mode="lines+markers", line=dict(width=2), marker=dict(size=4))
    fig_trafik.update_layout(
        height=450,
        plot_bgcolor="#1a1a19",
        paper_bgcolor="#1a1a19",
        font=dict(color="#c3c2b7"),
        title_font=dict(color="#ffffff", size=18),
        xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
    )
    st.plotly_chart(fig_trafik, use_container_width=True)
    st.caption(f"Son ölçüm: {trafik_df['TrafficIndexDate'].max()} · İndeks: {trafik_df.sort_values('TrafficIndexDate').iloc[-1]['TrafficIndex']}")
except Exception as e:
    st.error(f"Canlı trafik verisine ulaşılamadı: {e}")
