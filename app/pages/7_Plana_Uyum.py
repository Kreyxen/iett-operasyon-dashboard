"""
Plana Uyum

GetPlanaUyum_json servisi dokümante edilmiş ama pratikte çalışmıyor
(500 hatası, ölü servis). Bunun yerine GetIettArsivGorev_json'daki
planlanan vs gerçek başlangıç zamanı farkından kendi hesabımızı
türetiyoruz (src/plana_uyum.py). Tarih parametreli, günlük sorgulanır.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
from plana_uyum import gorevleri_cek, gecikme_hesapla  # noqa: E402
from planlanan_sefer import planlanan_sefer_sayisi, GUNTIPI_ETIKET, GUNTIPI_KODU  # noqa: E402
from tema import uygula as tema_uygula  # noqa: E402

ISTANBUL = ZoneInfo("Europe/Istanbul")
bugun_istanbul = datetime.now(ISTANBUL).date()

st.set_page_config(page_title="Plana Uyum", layout="wide")
tema_uygula()
st.title("Plana Uyum — Hat Bazlı Sefer Gecikmeleri")
st.caption(
    "Planlanan vs gerçekleşen sefer başlangıç zamanı farkından hesaplanır. "
    "Servis tarih bazlı sorgulanıyor (o günün verisi bir kerede geliyor), "
    "'canlı akan' bir veri değil ama güncel/gerçek."
)

secili_tarih = st.date_input(
    "Hangi günün verisine bakalım?",
    value=bugun_istanbul - timedelta(days=1),
    max_value=bugun_istanbul,
)


@st.cache_data(ttl=3600)
def veriyi_getir(tarih_str):
    kayitlar = gorevleri_cek(tarih_str)
    return gecikme_hesapla(kayitlar)


try:
    df = veriyi_getir(secili_tarih.strftime("%Y%m%d"))
except Exception as e:
    st.error(f"Servisten veri alınamadı: {e}")
    st.stop()

if df.empty:
    st.info("Bu gün için görev kaydı bulunamadı (gelecek bir tarih ya da veri henüz işlenmemiş olabilir).")
    st.stop()

zamaninda = (df["gecikme_dk"].abs() <= 5).sum()
col1, col2, col3 = st.columns(3)
col1.metric("Toplam görev", len(df))
col2.metric("Ortalama gecikme", f"{df['gecikme_dk'].mean():.1f} dk")
col3.metric("Zamanında (±5dk içinde)", f"%{100 * zamaninda / len(df):.1f}")

yon_secim = st.radio(
    "Görünüm",
    ["En çok geciken", "En dakik (plana en yakın)", "En erken kalkan"],
    horizontal=True,
)

st.subheader(f"{yon_secim} 15 Hat")
hat_ozet = (
    df.groupby("SHATKODU")["gecikme_dk"]
    .agg(["mean", "count"])
    .rename(columns={"mean": "ortalama_gecikme_dk", "count": "gorev_sayisi"})
    .query("gorev_sayisi >= 5")  # tek seferlik hatlar ortalamayı yanıltmasın
    .reset_index()
)
# "En dakik" = gecikme SIFIRA en yakın (erken de geç de olsa fark etmez).
# "En erken kalkan" = en BÜYÜK negatif değer (gerçekten erken kalkanlar).
# Düz artan sıralama "en dakik" için yanıltıcı olurdu (çok erken kalkan
# hatlar yanlışlıkla "az gecikmiş" görünürdü), bu yüzden ayırdık.
if yon_secim == "En dakik (plana en yakın)":
    hat_ozet["siralama_degeri"] = hat_ozet["ortalama_gecikme_dk"].abs()
    hat_ozet = hat_ozet.sort_values("siralama_degeri", ascending=True)
    renk = "#199e70"
elif yon_secim == "En erken kalkan":
    hat_ozet = hat_ozet.sort_values("ortalama_gecikme_dk", ascending=True)
    renk = "#3987e5"
else:
    hat_ozet = hat_ozet.sort_values("ortalama_gecikme_dk", ascending=False)
    renk = "#d95926"
hat_ozet = hat_ozet.head(15)

fig_bar = px.bar(
    hat_ozet,
    x="SHATKODU",
    y="ortalama_gecikme_dk",
    hover_data=["gorev_sayisi"],
    labels={"SHATKODU": "Hat", "ortalama_gecikme_dk": "Ortalama gecikme (dk)"},
    title=f"{yon_secim} hatlar (en az 5 görevi olan hatlar arasında)",
    template="plotly_dark",
    color_discrete_sequence=[renk],
)
fig_bar.update_layout(
    height=450,
    plot_bgcolor="#1a1a19",
    paper_bgcolor="#1a1a19",
    font=dict(color="#c3c2b7"),
    title_font=dict(color="#ffffff", size=18),
    xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
    yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
)
st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Gecikme Dağılımı")
fig_hist = px.histogram(
    df,
    x="gecikme_dk",
    nbins=60,
    labels={"gecikme_dk": "Gecikme (dk)", "count": "Görev sayısı"},
    title="Tüm görevlerin gecikme dağılımı (negatif = erken kalkış)",
    template="plotly_dark",
    color_discrete_sequence=["#3987e5"],
)
fig_hist.update_layout(
    height=400,
    plot_bgcolor="#1a1a19",
    paper_bgcolor="#1a1a19",
    font=dict(color="#c3c2b7"),
    title_font=dict(color="#ffffff", size=18),
    xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
    yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
)
st.plotly_chart(fig_hist, use_container_width=True)

hat_arama = st.text_input("Hat kodu ara (tabloyu filtrelemek için)")
gosterilecek = df
if hat_arama:
    gosterilecek = df[df["SHATKODU"].str.contains(hat_arama, case=False, na=False)]

with st.expander("Ham tablo"):
    st.dataframe(
        gosterilecek[["SHATKODU", "SKAPINUMARA", "planlanan", "gercek", "gecikme_dk"]],
        use_container_width=True,
    )

st.divider()

st.subheader("Planlanan vs Gerçekleşen Sefer Sayısı")
st.caption(
    "Ayrı bir servisten (GetPlanlananSeferSaati_json) o hattın seçili gün tipi için "
    "planlanan TÜM sefer sayısını çekip, yukarıdaki gerçekleşen sefer sayısıyla "
    "karşılaştırıyoruz. Bu, 'kaç sefer yapılması gerekiyordu' sorusuna GetPlanaUyum'un "
    "(çalışmayan servis) veremediği bir cevap."
)

gun_tipi_kodu = GUNTIPI_KODU[secili_tarih.weekday()]
st.caption(f"{secili_tarih.strftime('%d.%m.%Y')} -> gün tipi: **{GUNTIPI_ETIKET[gun_tipi_kodu]}**")

hat_secimi_planlanan = st.selectbox(
    "Bir hat seç",
    options=sorted(df["SHATKODU"].unique()),
    key="hat_secimi_planlanan",
)

if hat_secimi_planlanan:
    gercek_sefer_sayisi = len(df[df["SHATKODU"] == hat_secimi_planlanan])
    with st.spinner("Planlanan sefer saatleri çekiliyor..."):
        planlanan_sayisi = planlanan_sefer_sayisi(hat_secimi_planlanan, secili_tarih)

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Gerçekleşen Sefer", gercek_sefer_sayisi)
    if planlanan_sayisi is None:
        col_p2.metric("Planlanan Sefer", "—")
        col_p3.metric("Fark", "—")
        st.warning("Bu hat için planlanan sefer verisi alınamadı (servis o an yanıt vermemiş olabilir).")
    else:
        col_p2.metric("Planlanan Sefer", planlanan_sayisi)
        fark = gercek_sefer_sayisi - planlanan_sayisi
        col_p3.metric(
            "Fark",
            fark,
            delta=f"{'fazla' if fark > 0 else 'eksik' if fark < 0 else 'tam'}",
            delta_color="off",
        )
        if planlanan_sayisi > 0:
            oran = 100 * gercek_sefer_sayisi / planlanan_sayisi
            st.caption(f"Gerçekleşen / Planlanan oranı: %{oran:.1f}")

        fig_karsilastirma = px.bar(
            pd.DataFrame({
                "tur": ["Gerçekleşen", "Planlanan"],
                "sefer": [gercek_sefer_sayisi, planlanan_sayisi],
            }),
            x="sefer",
            y="tur",
            orientation="h",
            color="tur",
            color_discrete_map={"Gerçekleşen": "#3987e5", "Planlanan": "#199e70"},
            labels={"sefer": "Sefer Sayısı", "tur": ""},
            title=f"Hat {hat_secimi_planlanan} — Gerçekleşen vs Planlanan",
            template="plotly_dark",
        )
        fig_karsilastirma.update_layout(
            height=280,
            showlegend=False,
            plot_bgcolor="#1a1a19",
            paper_bgcolor="#1a1a19",
            font=dict(color="#c3c2b7"),
            title_font=dict(color="#ffffff", size=16),
            xaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
            yaxis=dict(gridcolor="#2c2c2a", zerolinecolor="#383835"),
        )
        st.plotly_chart(fig_karsilastirma, use_container_width=True)
