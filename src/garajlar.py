"""
DERS 17: Garaj/işletme bölgesi konumları (GetGaraj_json)

Daha önce hiç kullanmadığımız bir servis -- HatDurakGuzergah.asmx içinde
GetDurak/GetHat'in yanında duruyormuş, fark etmemiştik. İETT'nin 86
garaj/işletme bölgesinin adını ve koordinatını döndürüyor. Statik veri
(garajlar taşınmıyor), sık değişmediği için parametresiz.

KOORDINAT alanı "POINT (boylam enlem)" formatında düz metin geliyor,
diğer servislerin ayrı NBOYLAM/NENLEM sütunlarından farklı -- burada
parse edip enlem/boylam olarak ekliyoruz.
"""
import re

from api_client import soap_call, extract_json_result

PATH = "UlasimAnaVeri/HatDurakGuzergah.asmx"
METHOD = "GetGaraj_json"

_POINT_DESENI = re.compile(r"POINT \(([\d.]+) ([\d.]+)\)")


def garajlar():
    """Tüm garajların adı/kodu/enlem/boylamını döndürür."""
    xml_text = soap_call(PATH, METHOD, {})
    kayitlar = extract_json_result(xml_text, METHOD)
    for k in kayitlar:
        eslesme = _POINT_DESENI.match(k.get("KOORDINAT", "") or "")
        if eslesme:
            k["boylam"] = float(eslesme.group(1))
            k["enlem"] = float(eslesme.group(2))
        else:
            k["boylam"] = k["enlem"] = None
    return [k for k in kayitlar if k["enlem"] is not None]
