"""
DERS 4: Canlı filo konumu (GetFiloAracKonum_json)

Parametresiz çağrılıyor, tüm filonun (İETT + özel halk otobüsü
operatörleri) o anki konumunu döndürüyor. GetBozukSatih'ten farkı:
bu veri gerçekten CANLI -- "geçmiş" bir anlam taşımıyor, sadece
"şu an nerede" önemli. Bu yüzden diske arşivlemiyoruz; sayfa
(app/pages/3_Canli_Filo.py) bu fonksiyonu kısa süreli (60sn) bir
önbellekle çağırıyor.
"""
from api_client import soap_call, extract_json_result

PATH = "FiloDurum/SeferGerceklesme.asmx"
METHOD = "GetFiloAracKonum_json"


def filo_konumlari():
    """Servisi çağırır, filodaki tüm araçların anlık konum listesini döndürür."""
    xml_text = soap_call(PATH, METHOD, {})
    return extract_json_result(xml_text, METHOD)


def hat_konumlari(hat_kodu):
    """Belirli bir hattaki araçları + en yakın durak kodunu döndürür."""
    xml_text = soap_call(PATH, "GetHatOtoKonum_json", {"HatKodu": hat_kodu})
    return extract_json_result(xml_text, "GetHatOtoKonum_json")


if __name__ == "__main__":
    kayitlar = filo_konumlari()
    print(f"{len(kayitlar)} araç konumu geldi.")
    print(kayitlar[0])
