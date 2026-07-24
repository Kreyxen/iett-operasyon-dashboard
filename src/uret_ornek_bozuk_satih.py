"""
DERS 5: Sentetik (örnek/demo) bozuk satıh verisi üretmek

DİKKAT: Bu, GERÇEK veri DEĞİL. GetBozukSatih_json servisi az kayıt
döndürdüğü ve mentörden ek geçmiş veri alınamadığı için, dashboard'un
"çok veri olsaydı nasıl görünürdü" halini göstermek amacıyla üretilen
uydurma kayıtlardır. Her kayıt "kaynak" sütununda "Sentetik (Demo)"
olarak işaretlenir -- gerçek sistem verisiyle ASLA etiketsiz
karıştırılmaz, analiz/rapor sonuçlarına gerçekmiş gibi katılmamalıdır.

Koordinatlar, gerçek güzergah verisindeki (iett_guzergah.csv) durak
noktalarından rastgele seçilir -- böylece en azından İstanbul'daki
gerçek otobüs güzergahları üzerinde görünürler, rastgele denizin
ortasına düşmezler.
"""
import random
from pathlib import Path

import pandas as pd

PROJE_KOKU = Path(__file__).resolve().parent.parent
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"
GUZERGAH_YOLU = PROCESSED_KLASOR / "iett_guzergah.csv"

MESAJ_SECENEKLERI = ["BOZUK SATIH", "ÇUKUR VAR", "YOL ÇÖKMESİ", "ASFALT BOZUK", "KALDIRIM TAŞMASI"]

random.seed(42)  # tekrar üretilebilir olsun diye sabit tohum


def uret(adet=40):
    guzergah = pd.read_csv(GUZERGAH_YOLU)
    durak_noktalari = guzergah[["enlem", "boylam"]].drop_duplicates().sample(adet, random_state=42)

    simdi = pd.Timestamp.now()
    kayitlar = []
    for i, (_, nokta) in enumerate(durak_noktalari.iterrows()):
        kayitlar.append({
            "NMESAJID": 90000000 + i,
            "SKAPINUMARASI": f"DEMO-{random.randint(1000, 9999)}",
            "SSOFORSICILNO": str(random.randint(600000, 899999)),
            "SMESAJMETNI": random.choice(MESAJ_SECENEKLERI),
            "zaman": simdi - pd.Timedelta(hours=random.randint(1, 240)),
            "NBOYLAM": nokta["boylam"],
            "NENLEM": nokta["enlem"],
            "kaynak": "Sentetik (Demo)",
        })
    return pd.DataFrame(kayitlar)


if __name__ == "__main__":
    df = uret(adet=40)
    PROCESSED_KLASOR.mkdir(parents=True, exist_ok=True)
    hedef = PROCESSED_KLASOR / "bozuk_satih_sentetik.csv"
    df.to_csv(hedef, index=False)
    print(f"{len(df)} sentetik kayıt üretildi: {hedef}")
    print("UYARI: Bu veri gerçek değil, sadece demo amaçlı.")
