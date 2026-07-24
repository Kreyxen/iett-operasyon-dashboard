"""
DERS 2: SOAP servisinden ham veri çekmek (GetBozukSatih)

GetBozukSatih_json, şoförlerin bildirdiği bozuk yol noktalarını
döndürüyor. Servis parametresiz çağrılıyor ve sadece son birkaç
saatlik dar bir pencereyi gösteriyor (kendi geçmişini saklamıyor) --
bu yüzden her çalıştırmada dosyayı TARİHLİ bir isimle kaydediyoruz,
böylece servisin göstermediği geçmişi zamanla kendi arşivimizde
biriktirmiş oluyoruz.
"""

from datetime import datetime
from pathlib import Path
import json

from api_client import soap_call, extract_json_result

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_KLASOR = PROJE_KOKU / "data" / "raw"

PATH = "FiloDurum/SeferGerceklesme.asmx"
METHOD = "GetBozukSatih_json"


def cek():
    """Servisi çağırır, parse edilmiş kayıt listesini (dict listesi) döndürür."""
    xml_text = soap_call(PATH, METHOD, {})
    return extract_json_result(xml_text, METHOD)


if __name__ == "__main__":
    print(f"1) {METHOD} çağrılıyor...")
    kayitlar = cek()
    print(f"   -> {len(kayitlar)} kayıt geldi.")

    RAW_KLASOR.mkdir(parents=True, exist_ok=True)
    damga = datetime.now().strftime("%Y-%m-%d_%H%M")
    hedef_dosya = RAW_KLASOR / f"bozuk_satih_{damga}.json"
    with open(hedef_dosya, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)

    print(f"2) Ham veri kaydedildi: {hedef_dosya}")
