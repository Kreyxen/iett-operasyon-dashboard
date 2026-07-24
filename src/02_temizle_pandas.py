"""
DERS 2a: Ham JSON'u pandas ile temiz bir tabloya çevirmek

pandas, Python'da tablo (satır-sütun) verisiyle çalışmak için kullanılan
standart kütüphane. Excel'i Python içinden kullanmak gibi düşünebilirsin,
ama çok daha hızlı ve büyük veriyle çalışabilir.

Her pandas tablosuna "DataFrame" denir (kısaltması genelde "df").
"""

import pandas as pd
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_DOSYA = PROJE_KOKU / "data" / "raw" / "trafik_indeksi_raw.json"
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"

# ADIM 1: Ham JSON'u oku.
# pd.read_json bir JSON dosyasını doğrudan DataFrame'e çevirir.
df = pd.read_json(RAW_DOSYA)
print("HAM VERİ (ilk 3 satır):")
print(df.head(3))
print(f"\nToplam satır: {len(df)}, kolonlar: {list(df.columns)}")
print(f"\nKolon tipleri (dtypes):\n{df.dtypes}")
# dtype = "data type" (veri tipi). object = metin, int64 = tam sayı, float64 = ondalık sayı.
# trafficindexdate şu an "object", yani pandas onu düz METİN olarak görüyor, tarih olarak değil.

# ADIM 2: Gereksiz kolonu at.
# axis=1 demek "kolon sil" demek (axis=0 satır silmek olurdu).
df = df.drop(columns=["_id"])

# ADIM 3: Kolon isimlerini Türkçe ve anlaşılır yap.
df = df.rename(columns={
    "trafficindexdate": "tarih",
    "minimum_traffic_index": "min_trafik_indeksi",
    "maximum_traffic_index": "max_trafik_indeksi",
    "average_traffic_index": "ort_trafik_indeksi",
})

# ADIM 4: Tarih kolonunu GERÇEK tarih tipine çevir.
# pd.to_datetime, "2015-08-06T03:00:00" gibi bir metni pandas'ın anladığı
# bir "datetime" nesnesine çevirir. Bunu yapmazsak ileride "haziran ayındaki
# günleri getir" gibi bir filtre yazamayız -- pandas onu düz yazı sanır.
df["tarih"] = pd.to_datetime(df["tarih"]).dt.date  # saat kısmını atıp sadece gün bırakıyoruz (hepsi 03:00:00 zaten, anlamsız)

# ADIM 5: ort_trafik_indeksi kolonunu 2 basamağa yuvarla (57.858115775... okumak zor)
df["ort_trafik_indeksi"] = df["ort_trafik_indeksi"].round(2)

# ADIM 6: Tarihe göre sırala (ham veri zaten sıralıydı ama garanti olsun diye)
df = df.sort_values("tarih").reset_index(drop=True)

print("\n\nTEMİZ VERİ (ilk 3 satır):")
print(df.head(3))
print(f"\nYeni kolon tipleri:\n{df.dtypes}")

# ADIM 7: processed klasörüne CSV olarak kaydet.
PROCESSED_KLASOR.mkdir(parents=True, exist_ok=True)
hedef = PROCESSED_KLASOR / "trafik_indeksi.csv"
df.to_csv(hedef, index=False, encoding="utf-8-sig")
# index=False: pandas'ın kendi ürettiği 0,1,2... satır numarasını dosyaya YAZMA, zaten gerekmiyor
# encoding="utf-8-sig": Excel'in Türkçe karakterleri doğru göstermesi için gereken format

print(f"\nKaydedildi: {hedef}")
