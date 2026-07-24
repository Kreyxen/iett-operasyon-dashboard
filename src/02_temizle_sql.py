"""
DERS 2b: Aynı temizleme işini SQL ile yapmak (DuckDB kullanarak)

DuckDB, "analitik SQL motoru" denen bir araç. PostgreSQL/MySQL gibi ayrı
bir sunucu kurmana gerek yok -- bir kütüphane gibi Python'a dahil olur ve
CSV/JSON dosyalarını DOĞRUDAN SQL ile sorgulayabilirsin. Veri analisti
pozisyonlarının neredeyse tamamı SQL bilgisi ister; burada aynı mantığı
biraz önce pandas'ta yaptığımız işle birebir eşleştirerek öğreneceksin.

SQL = Structured Query Language. Cümleler İngilizce'ye yakın okunur:
"SELECT şu kolonları, FROM şu tablodan, WHERE şu şartla, ORDER BY şuna göre sırala"
"""

import duckdb
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_DOSYA = PROJE_KOKU / "data" / "raw" / "trafik_indeksi_raw.json"
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"

# DuckDB'ye bağlanıyoruz. ":memory:" demek "diskte dosya oluşturma, her şeyi
# RAM'de tut" demek -- küçük/orta veri için en pratik yöntem.
con = duckdb.connect(":memory:")

# ADIM 1+2+3+4+5 hepsi TEK bir SQL sorgusunda:
# read_json_auto() DuckDB'nin JSON dosyasını otomatik okuyup tablo gibi davranmasını sağlar.
sorgu = f"""
SELECT
    CAST(trafficindexdate AS DATE)          AS tarih,       -- CAST = tipi değiştir (metin -> tarih)
    minimum_traffic_index                    AS min_trafik_indeksi,
    maximum_traffic_index                    AS max_trafik_indeksi,
    ROUND(average_traffic_index, 2)          AS ort_trafik_indeksi   -- ROUND = pandas'taki .round(2) karşılığı
FROM read_json_auto('{RAW_DOSYA.as_posix()}')
ORDER BY tarih
"""

print("Çalıştırılan SQL sorgusu:")
print(sorgu)

# Sorguyu çalıştır ve sonucu pandas DataFrame olarak al (kontrol/karşılaştırma için pratik)
df = con.execute(sorgu).df()

print("SONUÇ (ilk 3 satır):")
print(df.head(3))
print(f"\nToplam satır: {len(df)}")

# ADIM 6: Kaydet -- DuckDB'nin kendi COPY komutuyla, SQL'den çıkmadan CSV yazabiliriz.
hedef = PROCESSED_KLASOR / "trafik_indeksi_sql.csv"
con.execute(f"COPY ({sorgu}) TO '{hedef.as_posix()}' (HEADER, DELIMITER ',')")
print(f"\nKaydedildi: {hedef}")

con.close()

# ---------------------------------------------------------------------------
# BONUS: pandas'taki "yeni kolon tipleri object" sorununu SQL'de yaşamıyoruz --
# CAST ile tarih net biçimde DATE tipine dönüşüyor. Bunu doğrula:
# ---------------------------------------------------------------------------
print("\npandas'ta okununca dtype:", )
import pandas as pd
kontrol = pd.read_csv(hedef)
print(kontrol.dtypes)
