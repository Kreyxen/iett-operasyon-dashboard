"""
DERS 3a: İki tabloyu JOIN ile birleştirmek (pandas .merge())

Amaç: "TALEP" (hangi hat, hangi saatte kaç yolcu taşıdı) ile
"ARZ" (hangi hat, hangi saatte kaç sefer yaptı) tablolarını birleştirip
tek bir tabloda hem yolcu hem sefer sayısını görebilmek.

İki tablonun BİRLEŞTİRME ANAHTARI (join key) ortak olan kolonlardır: hat + saat.
Bu ikisi aynı olan satırlar eşleştirilip yan yana konur.
"""

import pandas as pd
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW = PROJE_KOKU / "data" / "raw"
PROCESSED = PROJE_KOKU / "data" / "processed"

GUN = "2024-06-03"  # sadece bu dersi basit tutmak için tek bir güne odaklanıyoruz

# ---------------------------------------------------------------------------
# 1) TALEP tablosunu hazırla (BELBİM özetinden)
# ---------------------------------------------------------------------------
belbim = pd.read_parquet(RAW / "belbim_ozet_202406.parquet")
print("BELBİM ham hali (ilk 3 satır):")
print(belbim.head(3))

# Bu dosyada her satır: bir gün + bir saat + bir hat + bir İLÇE için yolcu sayısı.
# Biz ilçeyi önemsemiyoruz, o yüzden hat+saat bazında TOPLUYORUZ (groupby).
# groupby = "şu kolonlara göre grupla, sonra bir toplama fonksiyonu uygula"
talep = (
    belbim[belbim["transition_date"] == GUN]                  # sadece 3 Haziran
    .groupby(["line_name", "transition_hour"], as_index=False)  # hat+saat'e göre grupla
    ["number_of_passenger"].sum()                               # her grubun yolcusunu topla
    .rename(columns={"line_name": "hat", "transition_hour": "saat", "number_of_passenger": "yolcu"})
)
print(f"\nTALEP tablosu (gruplanmış, {GUN}), ilk 5 satır:")
print(talep.head())
print(f"Toplam satır: {len(talep)}")

# ---------------------------------------------------------------------------
# 2) ARZ tablosunu hazırla (görev arşivinden)
# ---------------------------------------------------------------------------
gorev = pd.read_parquet(RAW / f"gorev_{GUN}.parquet")
print(f"\nGÖREV ham hali (ilk 3 satır):")
print(gorev[["SHATKODU", "baslama_ts", "bitis_ts"]].head(3))

# baslama_ts saniye cinsinden "epoch" zaman damgası (1970'ten beri geçen saniye).
# Bunu okunabilir saate çevirmemiz lazım.
gorev = gorev[gorev["baslama_ts"].notna()].copy()  # başlamamış (iptal) seferleri at
zaman = pd.to_datetime(gorev["baslama_ts"], unit="s", utc=True).dt.tz_convert("Europe/Istanbul")
gorev["saat"] = zaman.dt.hour

# Her satır bir sefer -- hat+saat'e göre grupla, KAÇ TANE olduğunu say (size).
arz = (
    gorev.groupby(["SHATKODU", "saat"], as_index=False)
    .size()
    .rename(columns={"SHATKODU": "hat", "size": "sefer"})
)
print(f"\nARZ tablosu (gruplanmış, {GUN}), ilk 5 satır:")
print(arz.head())
print(f"Toplam satır: {len(arz)}")

# ---------------------------------------------------------------------------
# 3) JOIN: iki tabloyu hat+saat üzerinden birleştir
# ---------------------------------------------------------------------------
birlesik = talep.merge(arz, on=["hat", "saat"], how="inner")
birlesik["yolcu_per_sefer"] = (birlesik["yolcu"] / birlesik["sefer"]).round(1)

print(f"\nBİRLEŞİK tablo: {len(birlesik)} satır "
      f"(talep {len(talep)} satırdı, arz {len(arz)} satırdı -- eşleşmeyenler elendi)")

print("\n--- Hat 10, tüm saatler ---")
print(birlesik[birlesik["hat"] == "10"].sort_values("saat").to_string(index=False))

# ---------------------------------------------------------------------------
# 4) Kaydet
# ---------------------------------------------------------------------------
PROCESSED.mkdir(parents=True, exist_ok=True)
hedef = PROCESSED / f"talep_arz_birlesik_{GUN}.csv"
birlesik.to_csv(hedef, index=False, encoding="utf-8-sig")
print(f"\nKaydedildi: {hedef}")
