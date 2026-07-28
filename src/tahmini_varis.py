"""
DERS 18: Tahmini varış süresi (kendi hesabımız)

İETT'nin resmi "otobüs kaç dakikaya durağa gelir" servisi bizde çalışmıyor
(GetPlanlananSeferSaatiAraDurak_json ve GetDurakGecisZaman_IGA_json, ikisi de
500 hatası -- ölü servisler, bkz. plana_uyum.py'deki benzer notlar). Ama bunu
kendi verilerimizle tahmin edebiliyoruz:

  1) GetHatOtoKonum_json: aracın canlı konumu + o an EN YAKIN olduğu durak kodu
  2) iett_guzergah.csv: o hattın durak sırası (SIRANO) + her durağın koordinatı
  3) GetFiloAracKonum_json: aracın anlık hızı (GetHatOtoKonum_json'da hız yok,
     bu yüzden Kapı No üzerinden ayrıca eşleştiriyoruz)

Yöntem: aracın şu an en yakın olduğu duraktan hedef durağa kadar, ARADAKİ TÜM
DURAK SEGMENTLERİNİN kuş uçuşu (haversine) mesafesini toplayıp, aracın anlık
hızına bölüyoruz. Bu KABA bir tahmin -- trafik ışığı, duraklarda bekleme,
yol/kuş uçuşu farkı gibi şeyleri hesaba katmıyor, ama gerçek konum+hız
verisine dayanıyor (uydurma değil).
"""
import math
from pathlib import Path

import pandas as pd

from filo_konum import filo_konumlari, hat_konumlari

PROJE_KOKU = Path(__file__).resolve().parent.parent
GUZERGAH_YOLU = PROJE_KOKU / "data" / "processed" / "iett_guzergah.csv"

MIN_ETKIN_HIZ_KMH = 8  # araç trafik ışığında/durakta duruyor görünse bile makul bir alt sınır


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _guzergah_df():
    return pd.read_csv(GUZERGAH_YOLU)


def _segment_mesafeleri(yon_df):
    """Ardışık duraklar arası mesafeyi (km) hesaplayıp kümülatif toplam ekler."""
    df = yon_df.sort_values("SIRANO").reset_index(drop=True)
    mesafeler = [0.0]
    for i in range(1, len(df)):
        onceki, simdiki = df.iloc[i - 1], df.iloc[i]
        mesafeler.append(_haversine_km(onceki["enlem"], onceki["boylam"], simdiki["enlem"], simdiki["boylam"]))
    df = df.copy()
    df["kumulatif_km"] = pd.Series(mesafeler).cumsum()
    return df


def tahmini_varislar(hat_kodu, hedef_durak_kodu, en_fazla=5):
    """
    Bir hattın belirli bir durağına, o hattaki CANLI araçların tahmini varış
    sürelerini (dakika) döndürür. Hata durumunda {"hata": "..."} döner,
    başarılıysa {"tahminler": [{"kapino", "kalan_km", "anlik_hiz", "tahmini_dakika"}, ...]}.
    """
    guzergah = _guzergah_df()
    hat_df = guzergah[guzergah["HATKODU"].astype(str).str.lower() == hat_kodu.lower()]
    if hat_df.empty:
        return {"hata": f"'{hat_kodu}' hattı için güzergah verisi bulunamadı."}
    if str(hedef_durak_kodu) not in hat_df["DURAKKODU"].astype(str).values:
        return {"hata": f"Bu hat üzerinde '{hedef_durak_kodu}' kodlu durak bulunamadı."}

    try:
        canli_araclar = hat_konumlari(hat_kodu)
    except Exception as e:
        return {"hata": f"Canlı araç verisi alınamadı: {e}"}
    if not canli_araclar:
        return {"hata": f"'{hat_kodu}' hattında şu an sinyal veren araç yok."}

    try:
        tum_filo = filo_konumlari()
    except Exception:
        tum_filo = []
    hiz_haritasi = {}
    for a in tum_filo:
        try:
            hiz_haritasi[a.get("KapiNo")] = float(a.get("Hiz") or 0)
        except (TypeError, ValueError):
            pass

    yon_tablolari = {yon: _segment_mesafeleri(hat_df[hat_df["YON"] == yon]) for yon in hat_df["YON"].unique()}

    sonuclar = []
    for arac in canli_araclar:
        yakin_kod = str(arac.get("yakinDurakKodu"))
        for tablo in yon_tablolari.values():
            arac_satiri = tablo[tablo["DURAKKODU"].astype(str) == yakin_kod]
            hedef_satiri = tablo[tablo["DURAKKODU"].astype(str) == str(hedef_durak_kodu)]
            if arac_satiri.empty or hedef_satiri.empty:
                continue
            arac_km = arac_satiri.iloc[0]["kumulatif_km"]
            hedef_km = hedef_satiri.iloc[0]["kumulatif_km"]
            if hedef_km < arac_km:
                continue  # bu yönde hedef durağı zaten geçmiş, bu turda artık gelmeyecek
            kalan_km = hedef_km - arac_km
            hiz = hiz_haritasi.get(arac.get("kapino"), 0)
            etkin_hiz = max(hiz, MIN_ETKIN_HIZ_KMH)
            dakika = (kalan_km / etkin_hiz) * 60
            sonuclar.append({
                "kapino": arac.get("kapino"),
                "kalan_km": round(kalan_km, 2),
                "anlik_hiz": round(hiz, 1),
                "tahmini_dakika": round(dakika, 1),
            })
            break  # bu araç için doğru yön bulundu, aynı aracı diğer yönde tekrar sayma

    if not sonuclar:
        return {"hata": "Bu durağa şu an yaklaşan bir araç tespit edilemedi (araçlar durağı geçmiş olabilir)."}

    sonuclar.sort(key=lambda s: s["tahmini_dakika"])
    return {"tahminler": sonuclar[:en_fazla]}
