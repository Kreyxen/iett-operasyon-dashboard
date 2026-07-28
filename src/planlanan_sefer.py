"""
DERS 15: Planlanan sefer saatleri (GetPlanlananSeferSaati_json)

Daha önce hiç kullanmadığımız bir servis -- PlanlananSeferSaati.asmx.
Bir hattın ana duraktan (terminalden) planlanan TÜM kalkış saatlerini,
gün tipine (I=İş Günü, C=Cumartesi, P=Pazar) ve yöne (G/D) göre veriyor.

Aynı servisteki durak-durak versiyonu (GetPlanlananSeferSaatiAraDurak_json)
ve GetDurakGecisZaman_IGA_json denendi, ikisi de 500 hatası veriyor --
diğer "dokümante ama ölü" İETT servisleri gibi (bkz. GetPlanaUyum).

Bu veriyi src/plana_uyum.py'deki GERÇEKLEŞEN sefer sayısıyla karşılaştırarak
"bu hat bugün kaç sefer yapması planlanmıştı, kaçını gerçekten yaptı" sorusuna
cevap verebiliyoruz -- GetPlanaUyum'un veremediği, plana_uyum.py'nin de
(gecikme hesabı için) veremediği yeni bir açı.
"""
from pathlib import Path

import pandas as pd

from api_client import soap_call, extract_json_result

PATH = "UlasimAnaVeri/PlanlananSeferSaati.asmx"
METHOD = "GetPlanlananSeferSaati_json"

PROJE_KOKU = Path(__file__).resolve().parent.parent
GUZERGAH_YOLU = PROJE_KOKU / "data" / "processed" / "iett_guzergah.csv"

# İETT'nin gün tipi kodları: iş günü / cumartesi / pazar
GUNTIPI_KODU = {0: "I", 1: "I", 2: "I", 3: "I", 4: "I", 5: "C", 6: "P"}
GUNTIPI_ETIKET = {"I": "İş Günü", "C": "Cumartesi", "P": "Pazar"}


def planlanan_seferler(hat_kodu):
    """Bir hattın TÜM planlanan kalkış saatlerini (her gün tipi + yön için) döndürür."""
    xml_text = soap_call(PATH, METHOD, {"HatKodu": hat_kodu})
    return extract_json_result(xml_text, METHOD)


def planlanan_sefer_sayisi(hat_kodu, tarih):
    """
    `tarih` (datetime.date) gününe denk gelen gün tipi için planlanan sefer
    sayısını döndürür. Servis çalışmıyorsa ya da hat bulunamazsa None döner.
    """
    try:
        kayitlar = planlanan_seferler(hat_kodu)
    except Exception:
        return None
    gun_kodu = GUNTIPI_KODU[tarih.weekday()]
    return sum(1 for k in kayitlar if k.get("SGUNTIPI") == gun_kodu)


def _kalkis_yer_adlari(hat_kodu):
    """Her yön (G/D) için güzergahın İLK durağının adını döndürür -- 'nereden kalkıyor'."""
    if not GUZERGAH_YOLU.exists():
        return {}
    guzergah = pd.read_csv(GUZERGAH_YOLU)
    hat_g = guzergah[guzergah["HATKODU"].astype(str).str.lower() == hat_kodu.lower()]
    adlar = {}
    for yon in hat_g["YON"].unique():
        ilk = hat_g[hat_g["YON"] == yon].sort_values("SIRANO").iloc[0]
        adlar[yon] = ilk["DURAKADI"]
    return adlar


def hat_planlanan_detay(hat_kodu, tarih):
    """
    Tek SOAP çağrısıyla hem seçili tarihin gün tipine göre planlanan sefer
    SAYISINI hem de TÜM kalkış saatlerini (kalkış yerine ve gün tipine göre
    gruplu) döndürür. Servis çalışmazsa None döner.

    Dönüş: {"planlanan": int, "kalkis_saatleri": {kalkis_yeri: {gun_tipi: [saatler]}}}
    """
    try:
        kayitlar = planlanan_seferler(hat_kodu)
    except Exception:
        return None
    if not kayitlar:
        return None

    gun_kodu = GUNTIPI_KODU[tarih.weekday()]
    sayisi = sum(1 for k in kayitlar if k.get("SGUNTIPI") == gun_kodu)

    kalkis_adlari = _kalkis_yer_adlari(hat_kodu)
    gruplar = {}
    for k in kayitlar:
        kalkis_yeri = kalkis_adlari.get(k.get("SYON"), k.get("SYON"))
        gt_kodu = k.get("SGUNTIPI")
        gt_etiket = GUNTIPI_ETIKET.get(gt_kodu, gt_kodu)
        gruplar.setdefault(kalkis_yeri, {}).setdefault(gt_etiket, []).append(k.get("DT"))
    for kalkis_yeri, gt_gruplari in gruplar.items():
        for gt_etiket in gt_gruplari:
            gt_gruplari[gt_etiket] = sorted(set(gt_gruplari[gt_etiket]))

    return {"planlanan": sayisi, "kalkis_saatleri": gruplar}
