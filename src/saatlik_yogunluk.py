"""
DERS 6: Saatlik yolcu yoğunluğu (BELBİM turnike özeti)

data/raw/belbim_ozet_202406.parquet: her satır bir (tarih, saat, hat,
ilçe) kombinasyonunda kaç yolcu bindiğini gösteriyor (Haziran 2024,
559 bin satır). Bu dosya zaten "özet" haliyle geldiği için ayrı bir
temizleme script'i yazmadık -- sadece gün tipini (haftaiçi/haftasonu)
hesaplayan küçük bir yükleme fonksiyonu var, ağır iş (559 bin satır
okuma) burada tek yerde yapılıp sayfa tarafında önbelleklenir.
"""
from pathlib import Path

import pandas as pd

PROJE_KOKU = Path(__file__).resolve().parent.parent
VERI_YOLU = PROJE_KOKU / "data" / "raw" / "belbim_ozet_202406.parquet"


def veri_yukle():
    """Parquet'i okur, gün tipi (haftaiçi/haftasonu) sütunu ekler."""
    df = pd.read_parquet(VERI_YOLU)
    df["transition_date"] = pd.to_datetime(df["transition_date"])
    df["haftanin_gunu"] = df["transition_date"].dt.day_name()
    df["gun_tipi"] = df["haftanin_gunu"].isin(["Saturday", "Sunday"]).map(
        {True: "Hafta Sonu", False: "Hafta İçi"}
    )
    return df
