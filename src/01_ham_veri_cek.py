"""
DERS 1: Bir API'den ham veri çekmek

İBB'nin açık veri portalı (data.ibb.gov.tr) "CKAN" adlı bir sistem kullanıyor.
CKAN, dünyada birçok devlet kurumunun (ABD, İngiltere, AB dahil) kullandığı
açık kaynak bir "veri kataloğu" yazılımı. Yani burada öğrendiğin API mantığı
sadece İETT için değil, birçok açık veri portalı için geçerli.

API NEDİR? (Application Programming Interface)
Bir web sitesine tarayıcıyla girip veri görmek yerine, programının doğrudan
o siteye "bana şu veriyi JSON formatında ver" diye istek atmasıdır.
JSON = { "kolon1": deger1, "kolon2": deger2 } şeklinde, hem insanın hem
bilgisayarın kolay okuyabildiği bir veri formatı.

CKAN'ın veri sorgulama uç noktası (endpoint) şu şekilde çalışır:
https://data.ibb.gov.tr/api/3/action/datastore_search?resource_id=...&limit=...
"""

import requests  # HTTP istekleri atmak için standart Python kütüphanesi
import json
from pathlib import Path

# ADIM 0: Proje içindeki klasörlere göreceli yol tanımlıyoruz.
# __file__ = bu script'in kendi konumu. .parent.parent ile bir üst klasöre (iettyeni'ye) çıkıyoruz.
PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_KLASOR = PROJE_KOKU / "data" / "raw"

# ADIM 1: Hangi veri setini istediğimizi CKAN'a soruyoruz.
# "resource_id" her CSV/tablo için CKAN'ın verdiği benzersiz kimliktir.
# Önce paketin (dataset'in) bilgisini çekip içindeki resource_id'yi buluyoruz.
PACKAGE_SLUG = "istanbul-trafik-indeksi"
package_url = f"https://data.ibb.gov.tr/api/3/action/package_show?id={PACKAGE_SLUG}"

print(f"1) Paket bilgisi isteniyor: {package_url}")
r = requests.get(package_url, timeout=30)
r.raise_for_status()  # istek başarısızsa (404, 500 vb.) burada hata fırlatır, sessizce geçmez
paket = r.json()["result"]

resource_id = paket["resources"][0]["id"]
print(f"   -> Kaynak (resource) bulundu: {paket['resources'][0]['name']}  id={resource_id}")

# ADIM 2: Bu resource_id ile gerçek veriyi (satırları) istiyoruz.
# limit=5000 diyoruz çünkü verinin tamamı 3.332 satır, hepsini tek seferde alabiliriz.
veri_url = (
    "https://data.ibb.gov.tr/api/3/action/datastore_search"
    f"?resource_id={resource_id}&limit=5000"
)
print(f"\n2) Veri isteniyor: {veri_url}")
r = requests.get(veri_url, timeout=60)
r.raise_for_status()
sonuc = r.json()["result"]

kayitlar = sonuc["records"]  # bu bir Python listesi; her eleman bir satırı temsil eden dict
print(f"   -> {len(kayitlar)} satır geldi. İlk satır örneği:")
print(f"   {kayitlar[0]}")

# ADIM 3: Ham veriyi OLDUĞU GİBİ diske kaydediyoruz.
# Burada HİÇBİR temizlik, dönüştürme yapmıyoruz -- bu "raw" katmanının kuralı.
RAW_KLASOR.mkdir(parents=True, exist_ok=True)
hedef_dosya = RAW_KLASOR / "trafik_indeksi_raw.json"
with open(hedef_dosya, "w", encoding="utf-8") as f:
    json.dump(kayitlar, f, ensure_ascii=False, indent=2)

print(f"\n3) Ham veri kaydedildi: {hedef_dosya}")
print(f"   Dosya boyutu: {hedef_dosya.stat().st_size / 1024:.1f} KB")
