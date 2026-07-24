"""
DERS 7: Hat bazlı canlı duyurular (GetDuyurular_json)

Parametresiz çağrılıyor, TÜM hatların o anki duyurularını (sefer
iptalleri, güzergah değişiklikleri, yol kapanmaları) döndürüyor.
İki TIP değeri var: "Sefer" (belirli bir seferin iptali) ve
"Günlük" (genel/güzergah duyurusu).
"""
from api_client import soap_call, extract_json_result

PATH = "UlasimDinamikVeri/Duyurular.asmx"
METHOD = "GetDuyurular_json"


def duyurular():
    """Servisi çağırır, tüm hatların anlık duyuru listesini döndürür."""
    xml_text = soap_call(PATH, METHOD, {})
    return extract_json_result(xml_text, METHOD)
