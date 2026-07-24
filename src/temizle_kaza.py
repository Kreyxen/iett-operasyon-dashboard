"""
DERS 9: Ham kaza kayıtlarını işlemek

data/raw/kaza_*.json dosyalarını birleştirir, koordinatı eksik
(None) kayıtları atar, .NET tarih formatını okunaklı tarihe çevirir.
"""
from pathlib import Path
import json

import pandas as pd

from api_client import parse_dotnet_date

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_KLASOR = PROJE_KOKU / "data" / "raw"
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"


def ham_veriyi_yukle():
    kayitlar = []
    for dosya in sorted(RAW_KLASOR.glob("kaza_*.json")):
        with open(dosya, encoding="utf-8") as f:
            kayitlar.extend(json.load(f))
    return kayitlar


def isle(kayitlar):
    df = pd.DataFrame(kayitlar)
    if df.empty:
        return df

    df = df.dropna(subset=["BOYLAM", "ENLEM"])
    df["zaman"] = pd.to_datetime(df["KAZASAAT"].apply(parse_dotnet_date), unit="s")
    return df.sort_values("zaman", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    ham_kayitlar = ham_veriyi_yukle()
    print(f"1) {len(ham_kayitlar)} ham kayıt yüklendi.")

    df = isle(ham_kayitlar)
    print(f"2) Koordinatı eksik olanlar atıldıktan sonra {len(df)} kayıt kaldı.")

    PROCESSED_KLASOR.mkdir(parents=True, exist_ok=True)
    hedef_dosya = PROCESSED_KLASOR / "kaza_islenmis.csv"
    df.to_csv(hedef_dosya, index=False)
    print(f"3) İşlenmiş veri kaydedildi: {hedef_dosya}")
