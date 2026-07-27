"""
DERS 16: Günlük hat bazlı yolculuk sayısı (GetIettYolculukHat_json)

Daha önce hiç kullanmadığımız bir servis -- ibb360.asmx (GetIettArsivGorev_json
ile aynı dosya). Herhangi bir gün için (Tarih parametreli), o gün en çok
yolculuk yapan 50 hattın GERÇEK yolcu sayısını döndürüyor.

src/saatlik_yogunluk.py'deki BELBİM verisinden farkı: bu statik/arşiv değil,
istediğimiz güne canlı sorgu atabiliyoruz. Bugünün verisi gün bitmeden genelde
eksik/boş geliyor (bkz. plana_uyum.py'deki benzer not), o yüzden sayfada
varsayılan olarak dünü öneriyoruz.

Bazı kayıtlarda "Hat" alanı None geliyor (muhtemelen İETT dışı/otobüs
olmayan bir ulaşım modu) -- bunları çağıran taraf filtreliyor.
"""
from api_client import soap_call, extract_json_result

PATH = "ibb/ibb360.asmx"
METHOD = "GetIettYolculukHat_json"


def gunluk_hat_yolculuk(tarih_str):
    """tarih_str: 'YYYY-MM-DD'. O güne ait en çok yolculuk yapan 50 hattı döndürür."""
    xml_text = soap_call(PATH, METHOD, {"Tarih": tarih_str})
    return extract_json_result(xml_text, METHOD)
