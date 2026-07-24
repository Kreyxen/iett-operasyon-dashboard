"""
DERS 3b: Aynı JOIN işlemini SQL ile yapmak (DuckDB)

Fark: DuckDB parquet dosyalarını DOĞRUDAN okuyabilir (read_parquet(...)),
pandas'a hiç ihtiyaç duymadan. GROUP BY ve JOIN'i TEK bir SQL sorgusunda
birleştireceğiz -- pandas'ta iki ayrı adımda (önce groupby, sonra merge)
yaptığımız işi, SQL'de tek bir cümlede ifade edebiliyoruz.
"""

import duckdb
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW = PROJE_KOKU / "data" / "raw"
PROCESSED = PROJE_KOKU / "data" / "processed"
GUN = "2024-06-03"

con = duckdb.connect(":memory:")

sorgu = f"""
WITH talep AS (
    -- WITH ... AS: buna "CTE" (Common Table Expression) denir, SQL içinde
    -- geçici, isimlendirilmiş bir alt-tablo tanımlamanın yoludur.
    -- pandas'taki "önce talep değişkenini hesapla, sonra kullan" mantığının SQL karşılığı.
    SELECT
        line_name AS hat,
        transition_hour AS saat,
        SUM(number_of_passenger) AS yolcu     -- GROUP BY ile birlikte kullanılan toplama fonksiyonu
    FROM read_parquet('{(RAW / "belbim_ozet_202406.parquet").as_posix()}')
    WHERE transition_date = '{GUN}'
    GROUP BY line_name, transition_hour        -- pandas'taki .groupby(["line_name","transition_hour"])
),
arz AS (
    SELECT
        SHATKODU AS hat,
        EXTRACT(HOUR FROM (TO_TIMESTAMP(baslama_ts) AT TIME ZONE 'Europe/Istanbul')) AS saat,
        COUNT(*) AS sefer                      -- pandas'taki .size()
    FROM read_parquet('{(RAW / f"gorev_{GUN}.parquet").as_posix()}')
    WHERE baslama_ts IS NOT NULL
    GROUP BY SHATKODU, saat
)
SELECT
    t.hat, t.saat, t.yolcu, a.sefer,
    ROUND(t.yolcu * 1.0 / a.sefer, 1) AS yolcu_per_sefer
FROM talep AS t
INNER JOIN arz AS a
    ON t.hat = a.hat AND t.saat = a.saat        -- ON: iki tablo hangi kolonlarda eşleşecek
ORDER BY t.hat, t.saat
"""

print("Çalıştırılan SQL sorgusu:")
print(sorgu)

df = con.execute(sorgu).df()
print(f"\nBİRLEŞİK tablo: {len(df)} satır")
print("\n--- Hat 10, tüm saatler ---")
print(df[df["hat"] == "10"].to_string(index=False))

hedef = PROCESSED / f"talep_arz_birlesik_{GUN}_sql.csv"
con.execute(f"COPY ({sorgu}) TO '{hedef.as_posix()}' (HEADER, DELIMITER ',')")
print(f"\nKaydedildi: {hedef}")
con.close()
