"""
DERS 3: Ham GetBozukSatih kayıtlarını işlemek

- data/raw/ altındaki tüm bozuk_satih_*.json dosyalarını okur (script
  birden çok kez çalıştırıldıkça biriken arşiv).
- NMESAJID'e göre tekilleştirir (script art arda çalıştırılırsa
  servisin döndürdüğü zaman penceresi çakışabilir, aynı bildirim
  iki ayrı ham dosyada da görünebilir).
- .NET tarih formatını okunaklı tarihe çevirir.
- Koordinatları DBSCAN ile kümeler: aynı otobüsün/farklı otobüslerin
  birbirine yakın bildirimlerini "sıcak bölge" sayar. eps, metre
  cinsinden düşünülebilsin diye kabaca dereceye çevrilir (İstanbul
  enleminde ~1 derece ~100 km).
- Sonucu data/processed/bozuk_satih_islenmis.csv olarak kaydeder.
"""
from pathlib import Path
import json

import pandas as pd
from sklearn.cluster import DBSCAN

from api_client import parse_dotnet_date

PROJE_KOKU = Path(__file__).resolve().parent.parent
RAW_KLASOR = PROJE_KOKU / "data" / "raw"
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"

YARICAP_METRE = 150
EPS_DERECE = YARICAP_METRE / 100_000  # kaba çevrim: 1 derece ~ 100 km
MIN_SAMPLES = 2


def ham_veriyi_yukle():
    """data/raw altındaki tüm bozuk_satih_*.json dosyalarını okuyup birleştirir."""
    kayitlar = []
    for dosya in sorted(RAW_KLASOR.glob("bozuk_satih_*.json")):
        with open(dosya, encoding="utf-8") as f:
            kayitlar.extend(json.load(f))
    return kayitlar


def isle(kayitlar):
    """Ham kayıt listesini alır, tekilleştirilmiş + kümelenmiş DataFrame döndürür."""
    df = pd.DataFrame(kayitlar)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="NMESAJID")
    df["zaman"] = pd.to_datetime(df["DTKAYITZAMANI"].apply(parse_dotnet_date), unit="s")
    df["kaynak"] = "Sistem (İETT)"

    koordinatlar = df[["NENLEM", "NBOYLAM"]].to_numpy()
    kumeleme = DBSCAN(eps=EPS_DERECE, min_samples=MIN_SAMPLES).fit(koordinatlar)
    df["kume_id"] = kumeleme.labels_  # -1 = hiçbir kümeye girmeyen tekil nokta

    return df.sort_values("zaman", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    ham_kayitlar = ham_veriyi_yukle()
    print(f"1) {len(ham_kayitlar)} ham kayıt yüklendi ({RAW_KLASOR} altındaki tüm dosyalardan).")

    df = isle(ham_kayitlar)
    print(f"2) Tekilleştirme sonrası {len(df)} kayıt kaldı.")
    if not df.empty:
        kume_sayisi = df.loc[df["kume_id"] != -1, "kume_id"].nunique()
        kumeli_kayit = (df["kume_id"] != -1).sum()
        print(f"   -> {kume_sayisi} küme bulundu, {kumeli_kayit} kayıt bir kümeye ait.")

    PROCESSED_KLASOR.mkdir(parents=True, exist_ok=True)
    hedef_dosya = PROCESSED_KLASOR / "bozuk_satih_islenmis.csv"
    df.to_csv(hedef_dosya, index=False)
    print(f"3) İşlenmiş veri kaydedildi: {hedef_dosya}")
