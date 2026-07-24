"""
DERS 10-14: Claude (Anthropic) ile soru-cevap + gerçek veriye erişim (tool calling)

st.secrets üzerinden API anahtarını okuyoruz. Not: bu proje başlangıçta
Gemini (ücretsiz) kullanacak şekilde planlanmıştı, sonradan Claude API'ye
(ücretli, kullanıcı kendi isteğiyle) geçildi.

TOOL CALLING NASIL ÇALIŞIYOR (Anthropic'te Gemini'den farklı): Anthropic
fonksiyonları otomatik kabul etmiyor -- her aracın adını/açıklamasını/
parametre şeklini JSON olarak biz tanımlıyoruz (TOOLS listesi). Model
"şu aracı çağırmak istiyorum" dediğinde (stop_reason == "tool_use"),
BİZ ilgili Python fonksiyonunu çalıştırıp sonucu modele geri gönderiyoruz,
model de o sonucu okuyup insan diliyle cevap yazıyor. Bu yüzden tek
istek değil, çok adımlı bir döngü var (asagidaki while).
"""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
import pandas as pd
import streamlit as st

ISTANBUL = ZoneInfo("Europe/Istanbul")

from filo_konum import filo_konumlari, hat_konumlari
from duyurular import duyurular
from trafik_indeksi import trafik_gecmisi

PROJE_KOKU = Path(__file__).resolve().parent.parent
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"

MODEL = "claude-haiku-4-5-20251001"  # en ucuz/hızlı Claude modeli -- bu basit görevler için yeterli

SISTEM_TALIMATI = (
    "Sen İETT Operasyon Dashboard adlı bir staj projesinin asistanısın. "
    "İstanbul toplu taşıması hakkında kısa, net, Türkçe cevaplar ver.\n\n"
    "KESİN KURALLAR:\n"
    "1. Canlı/güncel veriyle ilgili HER soruda (araç sayısı, duyuru, arıza vb.) "
    "MUTLAKA ilgili aracı çağır. Kullanıcıyı 'dashboard'a bak' gibi "
    "yönlendirmelerle geçiştirme -- sen zaten o veriye aracınla ulaşabiliyorsun.\n"
    "2. Aracın döndürdüğü rakamların DIŞINDA hiçbir sayı/istatistik uydurma.\n"
    "3. SADECE İETT / İstanbul toplu taşıması / bu dashboard ile ilgili "
    "sorulara cevap ver. Konuyla alakasız bir soru gelirse (genel sohbet, "
    "başka bir konu, kod yazma isteği vb.) kibarca 'Ben sadece İETT "
    "Operasyon Dashboard ile ilgili sorulara yardımcı olabilirim' de ve "
    "başka hiçbir şey yazma -- hiçbir aracı çağırma, uzun açıklama yapma."
)

TOOLS = [
    {
        "name": "su_anki_filo_durumu",
        "description": "İETT filosundaki (tüm operatörler) toplam araç sayısını ve kaçının şu an hareket halinde olduğunu döndürür.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "aktif_duyurulari_getir",
        "description": "Hat bazlı aktif sefer iptali / güzergah değişikliği duyurularının sayısını, en son verileni ve birkaç örneğini döndürür.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "aktif_ariza_sayisi",
        "description": "Bozuk satıh (yol bozukluğu) bildirimlerinin toplam sayısını, kaynaklarına göre ayrılmış olarak döndürür.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "hat_bazli_arac_durumu",
        "description": (
            "Belirli bir hattaki (örn. '14ŞB', '34', '500T') araçların sayısını, "
            "kapı numaralarını ve en yakın durak bilgisini döndürür. Kullanıcı "
            "belirli bir hattı/otobüs numarasını adıyla sorduğunda bunu kullan, "
            "genel filo aracını değil."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Sorulan hattın kodu, örn. '14ŞB'"}
            },
            "required": ["hat_kodu"],
        },
    },
    {
        "name": "arac_ara",
        "description": "Plaka veya kapı numarasına göre belirli bir aracı filoda arar, bulursa konumunu/hızını/operatörünü döndürür.",
        "input_schema": {
            "type": "object",
            "properties": {
                "arama": {"type": "string", "description": "Plaka (örn. '34 HO 1000') veya kapı no (örn. 'M2595') -- tam ya da kısmi olabilir"}
            },
            "required": ["arama"],
        },
    },
    {
        "name": "verimlilik_hat_bilgisi",
        "description": "Belirli bir hattın verimlilik tier'ini (alt_ceyrek/orta_alt/orta_ust/ust_ceyrek), hat tipini (ana_arter/orta/tali/uzun_kirsal) ve temel istatistiklerini döndürür.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Sorulan hattın kodu, örn. '34'"}
            },
            "required": ["hat_kodu"],
        },
    },
    {
        "name": "guncel_trafik_indeksi",
        "description": "İstanbul genelinde şu anki (en son saatlik ölçüm) trafik yoğunluk indeksini (0-99 arası) döndürür.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "kaza_ozeti",
        "description": "Son 14 gündeki toplam kaza kaydı sayısını döndürür (İETT kaza lokasyon verisi -- sadece saat/koordinat var, hat/araç bilgisi yok).",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def su_anki_filo_durumu():
    kayitlar = filo_konumlari()
    toplam = len(kayitlar)
    hareket = 0
    for k in kayitlar:
        try:
            if float(k.get("Hiz") or 0) >= 5:
                hareket += 1
        except (TypeError, ValueError):
            pass
    return f"Şu an {toplam} araçtan sinyal geliyor, bunlardan yaklaşık {hareket} tanesi hareket halinde (5 km/h ve üzeri)."


def aktif_duyurulari_getir():
    kayitlar = duyurular()
    if not kayitlar:
        return "Şu an aktif duyuru yok."

    simdi = datetime.now(ISTANBUL).replace(tzinfo=None)

    def zamani_coz(k):
        eslesme = pd.Series([k.get("GUNCELLEME_SAATI", "")]).str.extract(r"(\d{2}:\d{2})")[0][0]
        if pd.isna(eslesme):
            return datetime.min
        saat = datetime.strptime(eslesme, "%H:%M").time()
        aday = datetime.combine(simdi.date(), saat)
        if aday > simdi:
            aday -= timedelta(days=1)
        return aday

    kayitlar_sirali = sorted(kayitlar, key=zamani_coz, reverse=True)
    en_son = kayitlar_sirali[0]
    en_son_metin = f"Hat {en_son['HATKODU']} ({en_son['HAT']}): {en_son['MESAJ']}"
    ornekler = " | ".join(f"Hat {k['HATKODU']}: {k['MESAJ'][:100]}" for k in kayitlar_sirali[1:4])
    return (
        f"Toplam {len(kayitlar)} aktif duyuru var. "
        f"EN SON verilen duyuru: {en_son_metin}. "
        f"Diğer birkaç örnek: {ornekler}"
    )


def aktif_ariza_sayisi():
    dosyalar = {
        "Sistem (İETT)": "bozuk_satih_islenmis.csv",
        "Sentetik (Demo)": "bozuk_satih_sentetik.csv",
        "Manuel Bildirim": "bozuk_satih_manuel.csv",
    }
    sonuc = []
    for etiket, dosya_adi in dosyalar.items():
        yol = PROCESSED_KLASOR / dosya_adi
        if yol.exists():
            sonuc.append(f"{etiket}: {len(pd.read_csv(yol))}")
    if not sonuc:
        return "Arıza verisi bulunamadı."
    return "Arıza bildirimi sayıları -> " + ", ".join(sonuc)


def hat_bazli_arac_durumu(hat_kodu):
    kayitlar = hat_konumlari(hat_kodu)
    if not kayitlar:
        return f"'{hat_kodu}' hattında şu an sinyal veren araç bulunamadı."
    hat_ad = kayitlar[0].get("hatad", "")
    yon = kayitlar[0].get("yon", "")
    detaylar = "; ".join(f"{k['kapino']} (durak: {k['yakinDurakKodu']})" for k in kayitlar[:8])
    return f"'{hat_kodu}' hattında ({hat_ad}, yön: {yon}) {len(kayitlar)} araç var. Örnekler: {detaylar}"


def arac_ara(arama):
    kayitlar = filo_konumlari()
    arama_temiz = arama.replace(" ", "").lower()
    eslesenler = [
        k for k in kayitlar
        if arama_temiz in str(k.get("Plaka", "")).replace(" ", "").lower()
        or arama_temiz in str(k.get("KapiNo", "")).replace(" ", "").lower()
    ]
    if not eslesenler:
        return f"'{arama}' ile eşleşen bir araç bulunamadı."
    detaylar = "; ".join(
        f"Plaka {k['Plaka']}, Kapı No {k['KapiNo']}, Hız {k['Hiz']} km/h, Operatör {k['Operator']}"
        for k in eslesenler[:5]
    )
    return f"{len(eslesenler)} eşleşme bulundu. {detaylar}"


def verimlilik_hat_bilgisi(hat_kodu):
    yol = PROCESSED_KLASOR / "hat_segmentleri.csv"
    if not yol.exists():
        return "Verimlilik verisi bulunamadı."
    df = pd.read_csv(yol)
    satir = df[df["hat_kodu"].astype(str).str.lower() == hat_kodu.lower()]
    if satir.empty:
        return f"'{hat_kodu}' hattı verimlilik verisinde bulunamadı."
    s = satir.iloc[0]
    return (
        f"Hat {s['hat_kodu']} ({s['SHATADI']}): verimlilik tier'i '{s['verimlilik_tier']}', "
        f"hat tipi '{s['hat_tipi_ad']}', ortalama yolcu/km oranı {s['ortalama_oran']:.2f}, "
        f"şüpheli kod eşleşmesi: {s['supheli_kod_eslesmesi']}."
    )


def guncel_trafik_indeksi():
    veri = trafik_gecmisi(gun=1, periyot="H")
    if not veri:
        return "Trafik indeksi verisi alınamadı."
    en_son = sorted(veri, key=lambda x: x["TrafficIndexDate"])[-1]
    return f"En son ölçüm ({en_son['TrafficIndexDate']}): trafik indeksi {en_son['TrafficIndex']} (0-99 arası)."


def kaza_ozeti():
    yol = PROCESSED_KLASOR / "kaza_islenmis.csv"
    if not yol.exists():
        return "Kaza verisi bulunamadı."
    df = pd.read_csv(yol)
    return f"Son 14 günde toplam {len(df)} kaza kaydı var."


ARAC_FONKSIYONLARI = {
    "su_anki_filo_durumu": su_anki_filo_durumu,
    "aktif_duyurulari_getir": aktif_duyurulari_getir,
    "aktif_ariza_sayisi": aktif_ariza_sayisi,
    "hat_bazli_arac_durumu": hat_bazli_arac_durumu,
    "arac_ara": arac_ara,
    "verimlilik_hat_bilgisi": verimlilik_hat_bilgisi,
    "guncel_trafik_indeksi": guncel_trafik_indeksi,
    "kaza_ozeti": kaza_ozeti,
}


def istemci():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


SOHBET_LOG_YOLU = PROCESSED_KLASOR / "sohbet_gecmisi.csv"


def sohbeti_kaydet(mesaj, cevap):
    """
    Her soru-cevabı bir CSV'ye ekliyor -- böylece dashboard'u paylaştığında
    kimin ne sorduğunu görebiliyorsun (bkz. app/pages/8_Sohbet_Gecmisi.py,
    şifreli).

    NOT: Streamlit Cloud'un dosya sistemi KALICI DEĞİL -- uygulama yeniden
    deploy edilirse (yeni bir push ile) bu dosya sıfırlanır. Kısa süreli
    paylaşım/demo için yeterli, uzun vadeli arşiv için değil.
    """
    satir = pd.DataFrame([{
        "zaman": datetime.now(ISTANBUL).strftime("%Y-%m-%d %H:%M:%S"),
        "soru": mesaj,
        "cevap": cevap,
    }])
    onceki = pd.read_csv(SOHBET_LOG_YOLU) if SOHBET_LOG_YOLU.exists() else pd.DataFrame()
    pd.concat([onceki, satir], ignore_index=True).to_csv(SOHBET_LOG_YOLU, index=False)


def soru_sor(mesaj):
    """Tek bir kullanıcı mesajını Claude'a gönderir, gerekirse araçları çalıştırır, cevap metnini döndürür."""
    client = istemci()
    mesajlar = [{"role": "user", "content": mesaj}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SISTEM_TALIMATI,
            tools=TOOLS,
            messages=mesajlar,
        )

        if response.stop_reason != "tool_use":
            # Model normal bir metin cevabı verdi, döngü bitti.
            cevap = "".join(blok.text for blok in response.content if blok.type == "text")
            try:
                sohbeti_kaydet(mesaj, cevap)
            except Exception:
                pass  # kayıt başarısız olsa bile kullanıcı cevabı almaya devam etsin
            return cevap

        # Model bir/birden fazla araç çağırmak istiyor -- hepsini çalıştırıp
        # sonuçları "tool_result" olarak modele geri gönderiyoruz.
        mesajlar.append({"role": "assistant", "content": response.content})
        arac_sonuclari = []
        for blok in response.content:
            if blok.type == "tool_use":
                fonksiyon = ARAC_FONKSIYONLARI[blok.name]
                sonuc = fonksiyon(**blok.input)
                arac_sonuclari.append({
                    "type": "tool_result",
                    "tool_use_id": blok.id,
                    "content": sonuc,
                })
        mesajlar.append({"role": "user", "content": arac_sonuclari})
