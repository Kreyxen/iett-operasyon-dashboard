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
from api_client import soap_call, extract_json_result

PATH = "UlasimAnaVeri/PlanlananSeferSaati.asmx"
METHOD = "GetPlanlananSeferSaati_json"

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
