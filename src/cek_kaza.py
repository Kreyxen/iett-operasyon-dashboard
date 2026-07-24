"""
DERS 8: Kaza lokasyon verisini çekmek (GetKazaLokasyon_json)

GetBozukSatih'ten farklı: bu servis parametresiz değil, TARİH
istiyor (yyyy-MM-dd) ve sadece o günün kazalarını döndürüyor --
"canlı pencere" değil, günlük sorgulanabilir bir servis. Bu yüzden
son N günü TEK TEK sorup, her günü ayrı bir ham dosyaya kaydediyoruz.
Zaten indirilmiş bir gün varsa tekrar sormuyoruz (gereksiz istek
atmamak için).

Alanlar sadece KAZASAAT, BOYLAM, ENLEM -- hat/plaka/araç bilgisi yok.
Bazı kayıtlarda koordinat None geliyor, temizleme adımında atılacak.
"""
from datetime import date, timedelta
from pathlib import Path
import json
import time

from api_client import soap_call, extract_json_result

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_KLASOR = PROJE_KOKU / "data" / "raw"

PATH = "FiloDurum/SeferGerceklesme.asmx"
METHOD = "GetKazaLokasyon_json"


def cek_gun(gun):
    tarih_str = gun.strftime("%Y-%m-%d")
    xml_text = soap_call(PATH, METHOD, {"Tarih": tarih_str})
    return extract_json_result(xml_text, METHOD)


if __name__ == "__main__":
    GUN_SAYISI = 14
    bugun = date.today()

    for i in range(GUN_SAYISI):
        gun = bugun - timedelta(days=i)
        hedef_dosya = RAW_KLASOR / f"kaza_{gun.strftime('%Y-%m-%d')}.json"
        if hedef_dosya.exists():
            print(f"{gun} zaten var, atlanıyor.")
            continue

        kayitlar = cek_gun(gun)
        RAW_KLASOR.mkdir(parents=True, exist_ok=True)
        with open(hedef_dosya, "w", encoding="utf-8") as f:
            json.dump(kayitlar, f, ensure_ascii=False, indent=2)
        print(f"{gun}: {len(kayitlar)} kayıt -> {hedef_dosya}")
        time.sleep(0.5)  # servise art arda çok hızlı istek atmamak için
