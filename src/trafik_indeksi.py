"""
DERS 12: Canlı trafik indeksi (İBB Trafik Yoğunluk Web Servisi)

Diğer servislerden farklı: SOAP değil, düz REST (GET) isteği.
data/processed/trafik_indeksi.csv (statik, 2024-10-18'de kesiliyordu)
yerine bunu kullanıyoruz -- bu gerçekten canlı, saatlik güncelleniyor.

Endpoint: /TrafficIndexHistory/{gun}/{periyot}
  gun    : kaç günlük geçmiş isteniyor
  periyot: "H" (saatlik), "D" (günlük), "5M" (5 dakikalık) vb.
"""
import requests

BASE = "https://api.ibb.gov.tr/tkmservices/api/TrafficData/v1/TrafficIndexHistory"


def trafik_gecmisi(gun=3, periyot="H"):
    """Son `gun` günün trafik indeksini `periyot` aralıklarla döndürür."""
    r = requests.get(f"{BASE}/{gun}/{periyot}", timeout=30)
    r.raise_for_status()
    return r.json()
