"""
DERS 11: Plana uyum (GetIettArsivGorev_json'dan türetilmiş)

GetPlanaUyum_json servisi dokümante edilmiş ama pratikte 500 hatası
veriyor (GetAkarYakitToplamLitre gibi ölü bir servis). Bunun yerine
GetIettArsivGorev_json'daki PLANLANAN vs GERÇEK başlangıç zamanı
farkından kendi "gecikme" hesabımızı türetiyoruz.

Tarih parametreli (yyyyMMdd), günlük sorgulanabilir -- "canlı pencere"
değil, istenen günün görev kayıtlarını tek seferde çekiyoruz.
"""
import pandas as pd

from api_client import soap_call, extract_json_result, parse_dotnet_date

PATH = "ibb/ibb360.asmx"
METHOD = "GetIettArsivGorev_json"


def gorevleri_cek(tarih_str):
    """tarih_str: 'yyyyMMdd' formatında (örn. '20260723')."""
    xml_text = soap_call(PATH, METHOD, {"Tarih": tarih_str})
    return extract_json_result(xml_text, METHOD)


def gecikme_hesapla(kayitlar):
    """Ham görev listesini alır, planlanan/gerçek zaman + gecikme (dk) sütunlarıyla DataFrame döndürür."""
    df = pd.DataFrame(kayitlar)
    if df.empty:
        return df

    df["planlanan"] = pd.to_datetime(df["DTPLANLANANBASLANGICZAMANI"].apply(parse_dotnet_date), unit="s")
    df["gercek"] = pd.to_datetime(df["DTBASLAMAZAMANI"].apply(parse_dotnet_date), unit="s")
    df["gecikme_dk"] = (df["gercek"] - df["planlanan"]).dt.total_seconds() / 60

    # Veri kalitesi: bazı kayıtlarda saat/tarih tutarsızlığından
    # gerçekçi olmayan uç değerler çıkabiliyor (örn. -500 dk ya da
    # +500 dk gibi). +/- 120 dakikanın dışını "güvenilmez" sayıp atıyoruz.
    df = df[df["gecikme_dk"].between(-120, 120)]
    return df
