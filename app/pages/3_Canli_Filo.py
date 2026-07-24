"""
M3: Canlı Filo Haritası

Mimari ilke (CLAUDE.md): sayfa veri çekmiyor, src/filo_konum.py'deki
fonksiyonu çağırıyor. Ama bu veri CANLI olduğu için (M2'deki gibi
işlenmiş bir CSV'ye değil), doğrudan servisten -- kısa süreli (60sn)
önbellekle -- okunuyor. st.cache_data(ttl=60): aynı 60 saniye
içinde sayfa yenilense bile SOAP isteği tekrar atılmaz.
"""
import sys
from pathlib import Path

import folium
from folium.plugins import FastMarkerCluster
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))
from filo_konum import filo_konumlari, hat_konumlari  # noqa: E402
from datetime import datetime  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

ISTANBUL = ZoneInfo("Europe/Istanbul")

st.set_page_config(page_title="Canlı Filo", layout="wide")
st.title("Canlı Filo — Anlık Araç Konumları")


@st.cache_data(ttl=60)
def veriyi_getir():
    kayitlar = filo_konumlari()
    df = pd.DataFrame(kayitlar)
    df["Hiz"] = pd.to_numeric(df["Hiz"], errors="coerce")
    df["Boylam"] = pd.to_numeric(df["Boylam"], errors="coerce")
    df["Enlem"] = pd.to_numeric(df["Enlem"], errors="coerce")
    df = df.dropna(subset=["Boylam", "Enlem"])

    # Saat alanı, aracın EN SON gönderdiği konumun saati -- "şu an" değil.
    # Bazı araçlar (garajda/GPS kapalı) saatler önceki son konumunda donmuş
    # olabilir. Gece yarısı sınırını da hesaba katarak (23:58 ile 00:02 arası
    # aslında sadece 4 dakika) "kaç dakika önce" hesaplıyoruz.
    # ÖNEMLİ: datetime.now() SUNUCUNUN kendi saat dilimini kullanır -- bu yerelde
    # Türkiye saatiyle aynıydı ama bulutta (Streamlit Cloud) genelde UTC'dir.
    # İETT'nin verdiği saat Türkiye saati olduğu için, biz de açıkça İstanbul
    # saatini kullanıyoruz (tzinfo'yu at, çünkü aday naive bir datetime).
    #.
    simdi = datetime.now(ISTANBUL).replace(tzinfo=None)

    def dakika_once(saat_str):
        try:
            saat = datetime.strptime(saat_str, "%H:%M:%S").time()
        except (TypeError, ValueError):
            return None
        aday = datetime.combine(simdi.date(), saat)
        fark = abs((simdi - aday).total_seconds()) / 60
        return min(fark, 1440 - fark)

    df["dakika_once"] = df["Saat"].apply(dakika_once)
    return df


col_baslik, col_buton = st.columns([4, 1])
with col_buton:
    if st.button("Yenile"):
        veriyi_getir.clear()

try:
    df = veriyi_getir()
except Exception as e:
    st.error(f"Servisten veri alınamadı: {e}")
    st.stop()

toplam_arac = len(df)
esik_dk = st.slider(
    "Kaç dakikaya kadar 'güncel' sayılsın?",
    min_value=5, max_value=60, value=15, step=5,
)
df = df[df["dakika_once"] <= esik_dk]

st.caption(
    f"{len(df)} / {toplam_arac} araç son {esik_dk} dakika içinde güncellenmiş "
    f"gösteriliyor (bayat GPS verisi olan araçlar filtrelendi). "
    f"Önbellek en fazla 60 saniye eski olabilir."
)

operatorler = sorted(df["Operator"].dropna().unique())
secili_operatorler = st.multiselect("Operatör", options=operatorler, default=operatorler)
df = df[df["Operator"].isin(secili_operatorler)]

secili_konum = None  # (enlem, boylam, plaka, kapino) -- hangi arama sonucundan gelirse gelsin

col_ara1, col_ara2 = st.columns(2)

with col_ara1:
    hat_kodu_girdi = st.text_input("Hat kodu ara (örn. 34, 522ST)")
    if hat_kodu_girdi:
        try:
            hat_kayitlari = hat_konumlari(hat_kodu_girdi)
        except Exception as e:
            hat_kayitlari = []
            st.error(f"Servisten veri alınamadı: {e}")

        if not hat_kayitlari:
            st.info("Bu hat için şu an araç bulunamadı.")
        else:
            hat_df = pd.DataFrame(hat_kayitlari)
            # GetHatOtoKonum_json plaka vermiyor -- üstte çektiğimiz tüm
            # filo verisiyle (Plaka var) Kapı No üzerinden eşleştiriyoruz.
            tum_filo = df[["KapiNo", "Plaka"]].drop_duplicates("KapiNo")
            hat_df = hat_df.merge(tum_filo, left_on="kapino", right_on="KapiNo", how="left")

            st.caption(f"{hat_df.iloc[0]['hatad']} ({hat_df.iloc[0]['yon']}) — {len(hat_df)} araç")
            hat_secim_key = f"hat_secim_{hat_kodu_girdi}"
            if hat_secim_key not in st.session_state:
                st.session_state[hat_secim_key] = None

            with st.container(height=200):
                for i, arac in hat_df.iterrows():
                    plaka_g = arac["Plaka"] if pd.notna(arac["Plaka"]) else "plaka yok"
                    etiket = (
                        f"{arac['kapino']} · {plaka_g} · durak: {arac['yakinDurakKodu']} "
                        f"· sinyal: {arac['son_konum_zamani']}"
                    )
                    if st.button(etiket, key=f"hat_btn_{hat_kodu_girdi}_{i}", use_container_width=True):
                        st.session_state[hat_secim_key] = i

            if st.session_state[hat_secim_key] is not None:
                secili = hat_df.iloc[st.session_state[hat_secim_key]]
                secili_konum = (secili["enlem"], secili["boylam"], secili["Plaka"], secili["kapino"])

with col_ara2:
    arama = st.text_input("Plaka veya kapı no ara")
    if arama:
        # Plaka "34 HO 1000" gibi boşluklu duruyor; kullanıcı boşluksuz
        # yazabilir ("34HO1000" ya da "HO1000" gibi) -- boşlukları
        # temizleyip öyle karşılaştırıyoruz.
        arama_temiz = arama.replace(" ", "")
        plaka_temiz = df["Plaka"].str.replace(" ", "", regex=False)
        kapino_temiz = df["KapiNo"].str.replace(" ", "", regex=False)

        bulunan = df[
            plaka_temiz.str.contains(arama_temiz, case=False, na=False)
            | kapino_temiz.str.contains(arama_temiz, case=False, na=False)
        ].reset_index(drop=True)

        if bulunan.empty:
            st.warning("Eşleşen araç bulunamadı (görünür filtrelerin dışında olabilir).")
        else:
            secim_key = f"arac_secim_{arama}"
            if secim_key not in st.session_state:
                st.session_state[secim_key] = None

            st.caption(f"{len(bulunan)} eşleşme")
            with st.container(height=200):
                for i, arac in bulunan.iterrows():
                    etiket = f"{arac['Plaka']} · Kapı No: {arac['KapiNo']} · {arac['Operator']}"
                    if st.button(etiket, key=f"arac_btn_{arama}_{i}", use_container_width=True):
                        st.session_state[secim_key] = i

            if st.session_state[secim_key] is not None:
                secili = bulunan.iloc[st.session_state[secim_key]]
                secili_konum = (secili["Enlem"], secili["Boylam"], secili["Plaka"], secili["KapiNo"])

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Gösterilen araç sayısı", len(df))
col_m2.metric("Duruyor (<5 km/h)", int((df["Hiz"] < 5).sum()))
col_m3.metric("Hareket halinde (≥5 km/h)", int((df["Hiz"] >= 5).sum()))

if secili_konum is not None:
    merkez = [secili_konum[0], secili_konum[1]]
    zoom = 16
else:
    merkez = [41.01, 29.0]
    zoom = 11

harita = folium.Map(location=merkez, zoom_start=zoom, tiles="cartodbpositron")

# FastMarkerCluster: MarkerCluster'dan farklı olarak binlerce nokta için
# Python tarafında tek tek nesne oluşturmuyor -- ham veriyi doğrudan
# tarayıcıya (JavaScript'e) gönderip işaretleri orada oluşturuyor. Renk/
# popup mantığı bu yüzden JS kodu olarak yazılıyor, Python'da değil.
veri = df[["Enlem", "Boylam", "Plaka", "KapiNo", "Hiz", "Operator"]].fillna("").values.tolist()

js_callback = """
function (row) {
    var hiz = parseFloat(row[4]);
    var renk = hiz < 5 ? '#e34948' : (hiz < 25 ? '#eda100' : '#1baf7a');
    var marker = L.circleMarker(new L.LatLng(row[0], row[1]), {
        radius: 5, color: renk, fillColor: renk, fillOpacity: 0.85, weight: 1
    });
    marker.bindPopup(
        'Plaka: ' + row[2] + '<br>' +
        'Kapı No: ' + row[3] + '<br>' +
        'Hız: ' + row[4] + ' km/h<br>' +
        'Operatör: ' + row[5]
    );
    return marker;
}
"""

FastMarkerCluster(data=veri, callback=js_callback).add_to(harita)

if secili_konum is not None:
    folium.CircleMarker(
        location=merkez,
        radius=11,
        color="#0d366b",
        fill=True,
        fill_color="#3987e5",
        fill_opacity=1.0,
        popup=f"Plaka: {secili_konum[2]}<br>Kapı No: {secili_konum[3]}",
    ).add_to(harita)

st.caption("🔴 <5 km/h (duruyor) · 🟡 5-25 km/h · 🟢 >25 km/h")

st_folium(harita, height=650, width=None, use_container_width=True, returned_objects=[])

st.subheader("Operatör Özeti")
ozet = (
    df.groupby("Operator")
    .agg(arac_sayisi=("KapiNo", "count"), ortalama_hiz=("Hiz", "mean"))
    .round(1)
    .sort_values("arac_sayisi", ascending=False)
    .reset_index()
)
st.dataframe(ozet, use_container_width=True)
