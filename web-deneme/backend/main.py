"""
DENEY: Streamlit dışı, özel tasarımlı bir arayüz denemesi.

Bu backend, ana projenin src/ klasöründeki fonksiyonları OLDUĞU GİBİ
kullanıyor (kopyalamıyor) -- veri çekme mantığı tek bir yerde kalsın
diye. Sadece bu fonksiyonların sonucunu JSON olarak dışarı veriyor,
frontend (web-deneme/frontend) bunu fetch() ile çekip gösteriyor.

Çalıştırma:
    venv/Scripts/python -m uvicorn web-deneme.backend.main:app --reload --port 8000
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE_KOKU / "src"))

from filo_konum import filo_konumlari, hat_konumlari  # noqa: E402
from duyurular import duyurular  # noqa: E402
from trafik_indeksi import trafik_gecmisi  # noqa: E402
from saatlik_yogunluk import veri_yukle  # noqa: E402
from plana_uyum import gorevleri_cek, gecikme_hesapla  # noqa: E402
from gunluk_yolculuk import gunluk_hat_yolculuk  # noqa: E402
from garajlar import garajlar  # noqa: E402
from planlanan_sefer import planlanan_sefer_sayisi  # noqa: E402
import asistan  # noqa: E402

PROCESSED = PROJE_KOKU / "data" / "processed"

ISTANBUL = ZoneInfo("Europe/Istanbul")

app = FastAPI(title="İETT Operasyon Merkezi -- Deney API")

# Frontend'i düz dosyadan (file://) ya da farklı bir localhost portundan
# açacağımız için tarayıcı CORS engeline takılmayalım diye açıyoruz.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Basit TTL önbellek (st.cache_data'nın elle yapılmış hali) ---
_onbellek: dict[str, tuple[float, object]] = {}


def _cache(anahtar, ttl_sn, uretici):
    kayit = _onbellek.get(anahtar)
    if kayit and (time.time() - kayit[0]) < ttl_sn:
        return kayit[1]
    deger = uretici()
    _onbellek[anahtar] = (time.time(), deger)
    return deger


def _dakika_once(saat_str, simdi):
    try:
        saat = datetime.strptime(saat_str, "%H:%M:%S").time()
    except (TypeError, ValueError):
        return None
    aday = datetime.combine(simdi.date(), saat)
    fark = abs((simdi - aday).total_seconds()) / 60
    return min(fark, 1440 - fark)


def _filo_hesapla():
    """Tüm filoyu (dakika_once dahil) döndürür -- 'güncel' eşiği frontend'de slider ile uygulanır (Streamlit'teki gibi)."""
    kayitlar = filo_konumlari()
    simdi = datetime.now(ISTANBUL).replace(tzinfo=None)
    sonuc = []
    for k in kayitlar:
        try:
            enlem, boylam, hiz = float(k["Enlem"]), float(k["Boylam"]), float(k["Hiz"])
        except (TypeError, ValueError, KeyError):
            continue
        dk = _dakika_once(k.get("Saat"), simdi)
        if dk is None:
            continue
        sonuc.append({
            "lat": enlem, "lon": boylam, "hiz": hiz,
            "plaka": k.get("Plaka"), "kapino": k.get("KapiNo"),
            "operator": k.get("Operator"), "dakika_once": round(dk, 1),
        })
    return sonuc


def _duyurular_sirali():
    kayitlar = duyurular()
    if not kayitlar:
        return []
    simdi = datetime.now(ISTANBUL).replace(tzinfo=None)

    def zamani_coz(k):
        eslesme = pd.Series([k.get("GUNCELLEME_SAATI", "")]).str.extract(r"(\d{2}:\d{2})")[0][0]
        if pd.isna(eslesme):
            return None
        saat = datetime.strptime(eslesme, "%H:%M").time()
        aday = datetime.combine(simdi.date(), saat)
        if aday > simdi:
            aday -= timedelta(days=1)
        return aday

    for k in kayitlar:
        gercek = zamani_coz(k)
        k["_gercek_zaman"] = gercek.isoformat() if gercek else None
    return sorted(kayitlar, key=lambda k: k["_gercek_zaman"] or "", reverse=True)


# Parquet (559 bin satır) her filtre kombinasyonunda diskten tekrar okunmasın
# diye ham veriyi bir kere yükleyip bellekte tutuyoruz -- Streamlit'te bunu
# st.cache_data yapıyordu, burada elle aynı şeyi yapıyoruz.
_YOGUNLUK_DF = None


def _yogunluk_df():
    global _YOGUNLUK_DF
    if _YOGUNLUK_DF is None:
        _YOGUNLUK_DF = veri_yukle()
    return _YOGUNLUK_DF


def _yogunluk_hesapla(ilceler=None, hat=None):
    df = _yogunluk_df()
    if ilceler:
        df = df[df["town"].isin(ilceler)]
    if hat:
        df = df[df["line_name"].str.contains(hat, case=False, na=False)]

    if df.empty:
        return {"saatlik": [], "ilce_ozet": [], "isi": [], "toplam_yolculuk": 0, "ilce_listesi": sorted(_yogunluk_df()["town"].dropna().unique().tolist())}

    saatlik_df = (
        df.groupby(["transition_hour", "gun_tipi"])
        .agg(toplam_yolcu=("number_of_passenger", "sum"), gun_sayisi=("transition_date", "nunique"))
        .reset_index()
    )
    saatlik_df["ortalama_yolcu"] = saatlik_df["toplam_yolcu"] / saatlik_df["gun_sayisi"]

    ilce_ozet = (
        df.groupby("town")["number_of_passenger"].sum().sort_values(ascending=False).reset_index()
        .rename(columns={"town": "ilce", "number_of_passenger": "toplam_yolcu"})
    )

    isi = df.groupby(["haftanin_gunu", "transition_hour"])["number_of_passenger"].mean().reset_index()
    isi.columns = ["gun", "saat", "ortalama_yolcu"]

    return {
        "saatlik": saatlik_df[["transition_hour", "gun_tipi", "ortalama_yolcu"]].to_dict(orient="records"),
        "ilce_ozet": ilce_ozet.to_dict(orient="records"),
        "isi": isi.to_dict(orient="records"),
        "toplam_yolculuk": int(df["number_of_passenger"].sum()),
        "ilce_listesi": sorted(_yogunluk_df()["town"].dropna().unique().tolist()),
    }


@app.get("/api/ozet")
def ozet():
    filo = [a for a in _cache("filo", 60, _filo_hesapla) if a["dakika_once"] <= 15]
    duyuru = _cache("duyurular", 120, duyurular)
    return {
        "canli_arac": len(filo),
        "ortalama_hiz": round(sum(a["hiz"] for a in filo) / len(filo), 1) if filo else 0,
        "aktif_duyuru": len(duyuru),
        "guncelleme": datetime.now(ISTANBUL).strftime("%H:%M:%S"),
    }


@app.get("/api/filo")
def filo():
    return _cache("filo", 60, _filo_hesapla)


@app.get("/api/filo/hat")
def filo_hat(hat_kodu: str):
    hat_kayitlari = hat_konumlari(hat_kodu)
    tum_filo = {a["kapino"]: a["plaka"] for a in _cache("filo", 60, _filo_hesapla)}
    for k in hat_kayitlari:
        k["plaka"] = tum_filo.get(k.get("kapino"))
    return hat_kayitlari


@app.get("/api/duyurular")
def duyurular_endpoint():
    return _cache("duyurular_sirali", 120, _duyurular_sirali)


@app.get("/api/trafik")
def trafik(gun: int = 3):
    return _cache(f"trafik_{gun}", 300, lambda: trafik_gecmisi(gun=gun, periyot="H"))


@app.get("/api/yogunluk")
def yogunluk(ilceler: str | None = None, hat: str | None = None):
    ilce_listesi = tuple(sorted(ilceler.split(","))) if ilceler else None
    anahtar = f"yogunluk_{ilce_listesi}_{hat}"
    return _cache(anahtar, 3600, lambda: _yogunluk_hesapla(ilce_listesi, hat))


def _verimlilik_yukle():
    yol = PROCESSED / "hat_segmentleri.csv"
    if not yol.exists():
        return []
    df = pd.read_csv(yol)
    return df[[
        "hat_kodu", "SHATADI", "verimlilik_tier", "hat_tipi_ad",
        "HAT_UZUNLUGU", "ortalama_oran", "ortalama_sefer", "ortalama_yolcu",
        "supheli_kod_eslesmesi",
    ]].to_dict(orient="records")


@app.get("/api/verimlilik")
def verimlilik():
    return _cache("verimlilik", 3600, _verimlilik_yukle)


def _ariza_yukle():
    dosyalar = ["bozuk_satih_islenmis.csv", "bozuk_satih_sentetik.csv", "bozuk_satih_manuel.csv"]
    parcalar = []
    for ad in dosyalar:
        yol = PROCESSED / ad
        if yol.exists():
            parcalar.append(pd.read_csv(yol, parse_dates=["zaman"]))
    if not parcalar:
        return []
    df = pd.concat(parcalar, ignore_index=True)
    df["zaman"] = df["zaman"].astype(str)
    df["kume_id"] = df["kume_id"].fillna(-1).astype(int)
    return df[["NENLEM", "NBOYLAM", "SMESAJMETNI", "SKAPINUMARASI", "zaman", "kaynak", "kume_id"]].to_dict(orient="records")


@app.get("/api/ariza")
def ariza():
    return _cache("ariza", 300, _ariza_yukle)


class ManuelArizaIstegi(BaseModel):
    enlem: float
    boylam: float
    mesaj: str
    kapino: str = ""
    sicil: str = ""


MANUEL_ARIZA_YOLU = PROCESSED / "bozuk_satih_manuel.csv"


@app.post("/api/ariza/manuel")
def ariza_manuel_ekle(istek: ManuelArizaIstegi):
    yeni_kayit = pd.DataFrame([{
        "NMESAJID": int(time.time()),
        "SKAPINUMARASI": istek.kapino or "BELİRTİLMEDİ",
        "SSOFORSICILNO": istek.sicil or "BELİRTİLMEDİ",
        "SMESAJMETNI": istek.mesaj,
        "zaman": datetime.now(ISTANBUL).replace(tzinfo=None),
        "NBOYLAM": istek.boylam,
        "NENLEM": istek.enlem,
        "kume_id": -1,
        "kaynak": "Manuel Bildirim",
    }])
    onceki = pd.read_csv(MANUEL_ARIZA_YOLU, parse_dates=["zaman"]) if MANUEL_ARIZA_YOLU.exists() else pd.DataFrame()
    pd.concat([onceki, yeni_kayit], ignore_index=True).to_csv(MANUEL_ARIZA_YOLU, index=False)
    _onbellek.pop("ariza", None)
    return {"basarili": True}


def _kaza_yukle():
    yol = PROCESSED / "kaza_islenmis.csv"
    if not yol.exists():
        return []
    df = pd.read_csv(yol, parse_dates=["zaman"])
    df["zaman"] = df["zaman"].astype(str)
    return df[["ENLEM", "BOYLAM", "zaman"]].to_dict(orient="records")


@app.get("/api/kaza")
def kaza():
    return _cache("kaza", 3600, _kaza_yukle)


GUZERGAH_YOLU = PROCESSED / "iett_guzergah.csv"


def _guzergah_yukle(hat_kodu):
    if not GUZERGAH_YOLU.exists():
        return []
    df = pd.read_csv(GUZERGAH_YOLU)
    df = df[df["HATKODU"].astype(str) == str(hat_kodu)].sort_values(["YON", "SIRANO"])
    return df[["YON", "SIRANO", "DURAKADI", "enlem", "boylam"]].to_dict(orient="records")


@app.get("/api/guzergah")
def guzergah(hat: str):
    return _cache(f"guzergah_{hat}", 3600, lambda: _guzergah_yukle(hat))


def _plana_uyum_hesapla(tarih_str):
    kayitlar = gorevleri_cek(tarih_str)
    df = gecikme_hesapla(kayitlar)
    if df.empty:
        return {"gorevler": [], "hat_ozet": []}
    hat_ozet = (
        df.groupby("SHATKODU")["gecikme_dk"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "ortalama_gecikme_dk", "count": "gorev_sayisi"})
        .query("gorev_sayisi >= 5")
        .reset_index()
        .to_dict(orient="records")
    )
    return {
        "gorevler": df[["SHATKODU", "SKAPINUMARA", "gecikme_dk"]].to_dict(orient="records"),
        "hat_ozet": hat_ozet,
    }


@app.get("/api/planauyum")
def planauyum(tarih: str | None = None):
    if tarih is None:
        dun = datetime.now(ISTANBUL) - timedelta(days=1)
        tarih = dun.strftime("%Y%m%d")
    return _cache(f"planauyum_{tarih}", 3600, lambda: _plana_uyum_hesapla(tarih))


def _gunluk_yolculuk_hesapla(tarih_str):
    kayitlar = gunluk_hat_yolculuk(tarih_str)
    return [k for k in kayitlar if k.get("Hat") is not None]


@app.get("/api/gunluk-yolculuk")
def gunluk_yolculuk(tarih: str):
    return _cache(f"gunluk_yolculuk_{tarih}", 3600, lambda: _gunluk_yolculuk_hesapla(tarih))


@app.get("/api/garajlar")
def garajlar_endpoint():
    return _cache("garajlar", 86400, garajlar)


@app.get("/api/planlanan-sefer")
def planlanan_sefer(hat: str, tarih: str):
    tarih_obj = datetime.strptime(tarih, "%Y%m%d").date()
    sayisi = _cache(f"planlanan_sefer_{hat}_{tarih}", 3600, lambda: planlanan_sefer_sayisi(hat, tarih_obj))
    return {"hat": hat, "planlanan": sayisi}


class SohbetIstegi(BaseModel):
    mesaj: str


@app.post("/api/asistan")
def asistan_sor(istek: SohbetIstegi):
    cevap = asistan.soru_sor(istek.mesaj)
    return {"cevap": cevap}
