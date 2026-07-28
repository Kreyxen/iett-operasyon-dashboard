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
import math
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
from garajlar import garajlar
from gunluk_yolculuk import gunluk_hat_yolculuk
from planlanan_sefer import planlanan_sefer_sayisi, planlanan_seferler
from tahmini_varis import tahmini_varislar
from api_client import soap_call, extract_json_result
import github_log

PROJE_KOKU = Path(__file__).resolve().parent.parent
PROCESSED_KLASOR = PROJE_KOKU / "data" / "processed"

MODEL = "claude-haiku-4-5-20251001"  # en ucuz/hızlı Claude modeli -- bu basit görevler için yeterli

DASHBOARD_BILGISI = (
    "Bu dashboard'un (İETT Operasyon Dashboard) sayfaları, verileri ve ne işe "
    "yaradıkları:\n"
    "- Ana Sayfa: genel özet metrikler (analiz edilen hat sayısı, toplam arıza, "
    "canlı araç/duyuru sayısı) + sen (AI asistan)\n"
    "- Verimlilik Gezgini: hat bazlı yolcu/km performansı, verimlilik tier'i "
    "(alt_çeyrek/orta_alt/orta_üst/üst_çeyrek), hat tipi (ana_arter/orta_yoğunluklu/"
    "tali_küçük/uzun_kırsal), güzergah haritası (durak durak, yön yön), o güzergahtaki "
    "arıza/kaza kesişimi. Bu sayfadaki güzergah verisini SEN de araçlarınla "
    "sorgulayabiliyorsun (hat_guzergahi, durak_ara)\n"
    "- Arıza Takip: bozuk satıh (yol bozukluğu) bildirimleri -- sistem (gerçek İETT "
    "verisi), sentetik (demo/uydurma, açıkça etiketli) ve manuel (kullanıcıların "
    "haritadan işaretleyip eklediği) olmak üzere 3 kaynaktan, DBSCAN ile kümelenmiş\n"
    "- Canlı Filo: filodaki TÜM araçların (6-7 bin civarı) anlık konumu, hız "
    "renklendirmesi, hat kodu arama, plaka/kapı no arama, operatör özeti, "
    "İETT'nin 86 garajının/işletme bölgesinin konumu (haritada ayrı katman)\n"
    "- Saatlik Yoğunluk: BELBİM yolcu verisiyle saatlik/günlük yoğunluk grafiği, "
    "gün x saat ısı haritası, canlı trafik indeksi trendi, VE ayrıca istenen "
    "herhangi bir güne canlı sorgu atıp o günün en çok yolculuk yapan 50 hattının "
    "gerçek yolcu sayısını gösteren ayrı bir bölüm (GetIettYolculukHat_json)\n"
    "- Duyurular: hat bazlı sefer iptali ve güzergah değişikliği duyuruları, canlı\n"
    "- Kaza Haritası: son 14 günün kaza kayıtları (sadece saat+koordinat, hat/araç "
    "bilgisi yok, İETT'nin kendi kısıtı)\n"
    "- Plana Uyum: hat bazında planlanan vs gerçek kalkış saati farkından "
    "hesaplanan gecikme analizi (GetPlanaUyum servisi çalışmadığı için kendi "
    "hesabımız), en çok geciken / en dakik / en erken kalkan hatlar, VE ayrıca bir "
    "hattın (GetPlanlananSeferSaati_json'dan) o gün PLANLANAN toplam sefer sayısını "
    "GERÇEKLEŞEN sayıyla karşılaştıran ayrı bir bölüm\n\n"
    "Kullanıcı 'bu sitede ne var', 'hangi sayfalar var', 'nereden bakabilirim' gibi "
    "sorular sorarsa bu bilgiyi kullanarak yol göster."
)

SISTEM_TALIMATI = (
    "Sen İETT Operasyon Dashboard adlı bir staj projesinin asistanısın. "
    "İstanbul toplu taşıması hakkında kısa, net, Türkçe cevaplar ver.\n\n"
    f"{DASHBOARD_BILGISI}\n\n"
    "KESİN KURALLAR:\n"
    "1. Canlı/güncel veriyle ilgili HER soruda (araç sayısı, duyuru, arıza vb.) "
    "MUTLAKA ilgili aracı çağır. Kullanıcıyı 'dashboard'a bak' gibi "
    "yönlendirmelerle geçiştirme -- sen zaten o veriye aracınla ulaşabiliyorsun.\n"
    "2. Aracın döndürdüğü rakamların DIŞINDA hiçbir sayı/istatistik uydurma.\n"
    "3. Konu kapsamın geniş: İETT, İstanbul toplu taşıması, otobüsler, "
    "trafik, hatlar, duraklar, ulaşım genel olarak -- bunlarla ilgili "
    "sorulara (dashboard'daki canlı veriyle ilgili olsun ya da genel "
    "bilgi sorusu olsun) seve seve cevap ver, kendi genel bilgini de "
    "kullanabilirsin, sadece araçların döndürdüğü veriyle sınırlı değilsin. "
    "Sadece TAMAMEN alakasız konularda (yemek tarifi, hava durumu, kod "
    "yazma isteği, genel sohbet vb.) kibarca 'Ben sadece İETT/toplu "
    "taşıma ile ilgili sorulara yardımcı olabilirim' de ve başka hiçbir "
    "şey yazma.\n"
    "4. Güzergah/durak/garaj/planlanan sefer/günlük yolculuk gibi sorularda da "
    "MUTLAKA ilgili aracı (hat_guzergahi, durak_ara, hat_en_yakin_garaj, "
    "arac_en_yakin_garaj, hat_planlanan_gercek_karsilastirma, en_yolcu_yogun_hatlar) "
    "çağır, kendi bilgine güvenip durak/koordinat uydurma.\n"
    "5. Önceki mesajları (varsa) hatırla -- kullanıcı 'o hat', 'o araç', 'M2595' gibi "
    "önceki cevapta geçen bir şeye atıfta bulunabilir, konuşma geçmişini dikkate al.\n"
    "6. Kalkış saatleri gibi listeler döndüren araçlarda (hat_kalkis_saatleri vb.) "
    "cevabını markdown ile düzenli formatla: kalkış yeri başlıkları KALIN, her gün "
    "tipi (Hafta İçi/Cumartesi/Pazar) ayrı bir satırda, saatler virgülle ayrılmış. "
    "otobus_tahmini_varis gibi TAHMİNİ verilerde bunun resmi değil kendi "
    "hesabımız/tahminimiz olduğunu kısaca belirt."
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
    {
        "name": "hat_guzergahi",
        "description": (
            "Bir hattın güzergahındaki durakları (kalkış, varış, ara duraklar, "
            "koordinatlar) döndürür. Kullanıcı 'X hattının güzergahını göster', "
            "'X hattı nereden nereye gidiyor' gibi sorduğunda bunu kullan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Hat kodu, örn. '14ŞB'"},
                "yon": {"type": "string", "description": "Opsiyonel: 'G' (Gidiş) veya 'D' (Dönüş). Boş bırakılırsa ilk bulunan yön kullanılır."},
            },
            "required": ["hat_kodu"],
        },
    },
    {
        "name": "durak_ara",
        "description": "Durak adına göre arama yapar; durak kodu, koordinatı ve o duraktan geçen hatları döndürür. Kullanıcı 'X durağını göster/bul' dediğinde bunu kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "durak_adi": {"type": "string", "description": "Aranan durağın adı (tam veya kısmi), örn. 'Ulus Caddesi'"}
            },
            "required": ["durak_adi"],
        },
    },
    {
        "name": "hat_en_yakin_garaj",
        "description": "Bir hattın kalkış durağına en yakın İETT garajını/işletme bölgesini döndürür. Kullanıcı 'X hattı için en yakın garaj neresi' dediğinde bunu kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Hat kodu, örn. '14ŞB'"}
            },
            "required": ["hat_kodu"],
        },
    },
    {
        "name": "arac_en_yakin_garaj",
        "description": (
            "Belirli bir aracın (plaka veya kapı no ile) ŞU ANKİ canlı konumuna en "
            "yakın garajı döndürür. Kullanıcı önce bir hattın aktif araçlarını "
            "listetip (hat_bazli_arac_durumu) sonra 'şu araca en yakın garaj neresi' "
            "diye kapı no vererek sorduğunda bunu kullan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "arama": {"type": "string", "description": "Plaka veya kapı no, örn. 'M2595'"}
            },
            "required": ["arama"],
        },
    },
    {
        "name": "hat_planlanan_gercek_karsilastirma",
        "description": "Bir hattın belirli bir gün için PLANLANAN toplam sefer sayısını döndürür (dünün verisi varsayılan). Kullanıcı 'X hattı bugün/dün kaç sefer yapması gerekiyordu' gibi sorduğunda bunu kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Hat kodu, örn. '34'"},
                "tarih": {"type": "string", "description": "Opsiyonel, YYYY-MM-DD formatında. Boş bırakılırsa dün kullanılır."},
            },
            "required": ["hat_kodu"],
        },
    },
    {
        "name": "hat_kalkis_saatleri",
        "description": "Bir hattın ana duraktan planlanan TÜM kalkış saatlerini (kalkış yerine ve gün tipine -- Hafta İçi/Cumartesi/Pazar -- göre gruplu) döndürür. Kullanıcı 'X hattının kalkış/sefer saatleri nedir' dediğinde bunu kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Hat kodu, örn. '132H'"}
            },
            "required": ["hat_kodu"],
        },
    },
    {
        "name": "otobus_tahmini_varis",
        "description": (
            "Bir hattın canlı araçlarının, adı verilen durağa TAHMİNİ varış "
            "sürelerini (dakika) döndürür -- resmi bir servis değil, canlı konum+hız "
            "verisinden bizim hesapladığımız kaba bir tahmin. Kullanıcı 'X hattı Y "
            "durağına kaç dakikaya gelir' gibi sorduğunda bunu kullan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hat_kodu": {"type": "string", "description": "Hat kodu, örn. '14ŞB'"},
                "durak_adi": {"type": "string", "description": "Durak adı (tam veya kısmi), örn. 'Ulus Caddesi'"},
            },
            "required": ["hat_kodu", "durak_adi"],
        },
    },
    {
        "name": "en_yolcu_yogun_hatlar",
        "description": "Belirli bir güne ait (varsayılan dün) en çok yolculuk yapan hatları gerçek yolcu sayılarıyla döndürür. Kullanıcı 'hangi hat en çok yolcu taşıyor', 'en yoğun hatlar hangisi' gibi sorduğunda bunu kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tarih": {"type": "string", "description": "Opsiyonel, YYYY-MM-DD formatında. Boş bırakılırsa dün kullanılır."}
            },
        },
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


GUZERGAH_YOLU = PROCESSED_KLASOR / "iett_guzergah.csv"

_TR_HARITASI = str.maketrans("şŞıİğĞüÜöÖçÇ", "sSiIgGuUoOcC")


def _normalize(s):
    """Türkçe karakterleri ASCII karşılığına çevirip küçük harfe indirir --
    kullanıcı 'Kuyubasi' yazsa da veride 'KUYUBAŞI' geçse de eşleşsin diye."""
    return str(s).translate(_TR_HARITASI).lower()


def _guzergah_df():
    return pd.read_csv(GUZERGAH_YOLU)


def hat_guzergahi(hat_kodu, yon=None):
    df = _guzergah_df()
    hat_df = df[df["HATKODU"].astype(str).str.lower() == hat_kodu.lower()]
    if hat_df.empty:
        return f"'{hat_kodu}' hattı için güzergah verisi bulunamadı."
    if not yon:
        yon = sorted(hat_df["YON"].unique())[0]
    secili = hat_df[hat_df["YON"] == yon].sort_values("SIRANO")
    if secili.empty:
        return f"'{hat_kodu}' hattının '{yon}' yönü için durak bulunamadı."
    ilk, son = secili.iloc[0], secili.iloc[-1]
    ara_duraklar = ", ".join(secili.iloc[1:-1]["DURAKADI"].tolist()[:10])
    fazla_var = "..." if len(secili) > 12 else ""
    return (
        f"Hat {hat_kodu} ({'Gidiş' if yon == 'G' else 'Dönüş'} yönü): {len(secili)} durak. "
        f"Kalkış: {ilk['DURAKADI']} ({ilk['enlem']:.5f}, {ilk['boylam']:.5f}). "
        f"Varış: {son['DURAKADI']} ({son['enlem']:.5f}, {son['boylam']:.5f}). "
        f"Aradaki bazı duraklar: {ara_duraklar}{fazla_var}. "
        "Tam güzergahı haritada görmek için Verimlilik Gezgini sayfasındaki "
        "'Güzergah Haritası' bölümünden bu hattı seçebilirsin."
    )


def durak_ara(durak_adi):
    df = _guzergah_df()
    aranan = _normalize(durak_adi)
    eslesenler = df[df["DURAKADI"].apply(_normalize).str.contains(aranan, na=False)].drop_duplicates("DURAKKODU")
    if eslesenler.empty:
        return f"'{durak_adi}' adında bir durak bulunamadı."
    hatlar = sorted(eslesenler["HATKODU"].astype(str).unique())
    ilk = eslesenler.iloc[0]
    hat_ornekleri = ", ".join(hatlar[:15])

    detay = ""
    try:
        xml = soap_call("UlasimAnaVeri/HatDurakGuzergah.asmx", "GetDurak_json", {"DurakKodu": str(ilk["DURAKKODU"])})
        sonuc = extract_json_result(xml, "GetDurak_json")
        if sonuc:
            d = sonuc[0]
            detay = f" Akıllı durak: {d.get('AKILLI', '?')}. Engelli erişimi: {d.get('ENGELLIKULLANIM', '?')}."
    except Exception:
        pass  # erişilebilirlik detayı alınamazsa temel bilgiyle devam et

    return (
        f"'{durak_adi}' araması için {len(eslesenler)} durak bulundu. "
        f"İlk eşleşme: {ilk['DURAKADI']} (durak kodu: {ilk['DURAKKODU']}, "
        f"koordinat: {ilk['enlem']:.5f}, {ilk['boylam']:.5f}).{detay} "
        f"Bu durağı kullanan hatlardan bazıları: {hat_ornekleri}."
    )


def hat_kalkis_saatleri(hat_kodu):
    """Bir hattın ana duraktan planlanan TÜM kalkış saatlerini, kalkış yerine ve gün tipine göre gruplu metin olarak döndürür."""
    try:
        kayitlar = planlanan_seferler(hat_kodu)
    except Exception as e:
        return f"Planlanan sefer saatleri alınamadı: {e}"
    if not kayitlar:
        return f"'{hat_kodu}' hattı için planlanan sefer saati bulunamadı."

    guzergah = _guzergah_df()
    hat_g = guzergah[guzergah["HATKODU"].astype(str).str.lower() == hat_kodu.lower()]
    kalkis_adlari = {}
    for yon in hat_g["YON"].unique():
        ilk = hat_g[hat_g["YON"] == yon].sort_values("SIRANO").iloc[0]
        kalkis_adlari[yon] = ilk["DURAKADI"]

    gun_etiket = {"I": "Hafta İçi", "C": "Cumartesi", "P": "Pazar"}
    gruplar = {}
    for k in kayitlar:
        kalkis_yeri = kalkis_adlari.get(k.get("SYON"), k.get("SYON"))
        gun_tipi = gun_etiket.get(k.get("SGUNTIPI"), k.get("SGUNTIPI"))
        gruplar.setdefault(kalkis_yeri, {}).setdefault(gun_tipi, []).append(k.get("DT"))

    parcalar = []
    for kalkis_yeri, gun_gruplari in gruplar.items():
        parcalar.append(f"{kalkis_yeri} KALKIŞ:")
        for gun_tipi in ["Hafta İçi", "Cumartesi", "Pazar"]:
            saatler = sorted(set(gun_gruplari.get(gun_tipi, [])))
            if not saatler:
                continue
            if len(saatler) > 16:
                gosterilecek = ", ".join(saatler[:12]) + f" ... (toplam {len(saatler)} sefer)"
            else:
                gosterilecek = ", ".join(saatler)
            parcalar.append(f"  {gun_tipi}: {gosterilecek}")
    return "\n".join(parcalar)


def otobus_tahmini_varis(hat_kodu, durak_adi):
    """Bir hattın canlı araçlarının, adı verilen durağa tahmini varış sürelerini döndürür."""
    guzergah = _guzergah_df()
    hat_g = guzergah[guzergah["HATKODU"].astype(str).str.lower() == hat_kodu.lower()]
    if hat_g.empty:
        return f"'{hat_kodu}' hattı için güzergah verisi bulunamadı."
    aranan = _normalize(durak_adi)
    eslesen_durak = hat_g[hat_g["DURAKADI"].apply(_normalize).str.contains(aranan, na=False)]
    if eslesen_durak.empty:
        return f"'{hat_kodu}' hattı üzerinde '{durak_adi}' adında bir durak bulunamadı."
    durak_kodu = eslesen_durak.iloc[0]["DURAKKODU"]
    durak_ad_gercek = eslesen_durak.iloc[0]["DURAKADI"]

    sonuc = tahmini_varislar(hat_kodu, durak_kodu)
    if "hata" in sonuc:
        return sonuc["hata"]

    satirlar = [
        f"{t['kapino']} (kapı no) -> ~{t['tahmini_dakika']:.0f} dakika (kalan {t['kalan_km']} km, anlık hız {t['anlik_hiz']} km/h)"
        for t in sonuc["tahminler"]
    ]
    return (
        f"Hat {hat_kodu}, {durak_ad_gercek} durağına tahmini varışlar (KABA tahmin -- "
        "canlı konum ve hıza dayalı, trafik ışığı/bekleme hesaba katılmıyor):\n"
        + "\n".join(satirlar)
    )


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _en_yakin_garaj(enlem, boylam):
    en_yakin, en_mesafe = None, float("inf")
    for g in garajlar():
        mesafe = _haversine_km(enlem, boylam, g["enlem"], g["boylam"])
        if mesafe < en_mesafe:
            en_mesafe, en_yakin = mesafe, g
    return en_yakin, en_mesafe


def hat_en_yakin_garaj(hat_kodu):
    df = _guzergah_df()
    hat_df = df[df["HATKODU"].astype(str).str.lower() == hat_kodu.lower()]
    if hat_df.empty:
        return f"'{hat_kodu}' hattı bulunamadı."
    ilk_durak = hat_df.sort_values("SIRANO").iloc[0]
    garaj, mesafe = _en_yakin_garaj(ilk_durak["enlem"], ilk_durak["boylam"])
    if garaj is None:
        return "Garaj verisi alınamadı."
    return (
        f"Hat {hat_kodu}'nin kalkış durağına ({ilk_durak['DURAKADI']}) en yakın garaj: "
        f"{garaj['GARAJ_ADI']} (~{mesafe:.1f} km uzaklıkta)."
    )


def arac_en_yakin_garaj(arama):
    kayitlar = filo_konumlari()
    arama_temiz = arama.replace(" ", "").lower()
    eslesen = next(
        (
            k for k in kayitlar
            if arama_temiz in str(k.get("Plaka", "")).replace(" ", "").lower()
            or arama_temiz in str(k.get("KapiNo", "")).lower()
        ),
        None,
    )
    if not eslesen:
        return f"'{arama}' ile eşleşen bir araç bulunamadı."
    try:
        enlem, boylam = float(eslesen["Enlem"]), float(eslesen["Boylam"])
    except (TypeError, ValueError):
        return "Aracın konum bilgisi geçersiz."
    garaj, mesafe = _en_yakin_garaj(enlem, boylam)
    if garaj is None:
        return "Garaj verisi alınamadı."
    return (
        f"{eslesen.get('Plaka')} (Kapı No: {eslesen.get('KapiNo')}) aracının şu anki "
        f"konumuna en yakın garaj: {garaj['GARAJ_ADI']} (~{mesafe:.1f} km uzaklıkta)."
    )


def hat_planlanan_gercek_karsilastirma(hat_kodu, tarih=None):
    if tarih:
        tarih_obj = datetime.strptime(tarih, "%Y-%m-%d").date()
    else:
        tarih_obj = datetime.now(ISTANBUL).date() - timedelta(days=1)
    planlanan = planlanan_sefer_sayisi(hat_kodu, tarih_obj)
    if planlanan is None:
        return f"'{hat_kodu}' hattı için planlanan sefer verisi alınamadı (servis o an yanıt vermemiş olabilir)."
    return (
        f"Hat {hat_kodu} için {tarih_obj.strftime('%d.%m.%Y')} tarihinde planlanan "
        f"toplam sefer sayısı: {planlanan}. Gerçekleşen sayıyla karşılaştırmak için "
        "Plana Uyum sayfasındaki 'Planlanan vs Gerçekleşen Sefer Sayısı' bölümüne bakabilirsin."
    )


def en_yolcu_yogun_hatlar(tarih=None):
    tarih_str = tarih or (datetime.now(ISTANBUL) - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        kayitlar = [k for k in gunluk_hat_yolculuk(tarih_str) if k.get("Hat")]
    except Exception as e:
        return f"Veri alınamadı: {e}"
    if not kayitlar:
        return f"{tarih_str} için veri bulunamadı (gün bitmeden veri gelmeyebilir)."
    kayitlar.sort(key=lambda k: k["Yolculuk"], reverse=True)
    ilk5 = "; ".join(f"{k['Hat']}: {k['Yolculuk']:,}".replace(",", ".") for k in kayitlar[:5])
    return f"{tarih_str} tarihinde en çok yolculuk yapan hatlar: {ilk5}."


ARAC_FONKSIYONLARI = {
    "su_anki_filo_durumu": su_anki_filo_durumu,
    "aktif_duyurulari_getir": aktif_duyurulari_getir,
    "aktif_ariza_sayisi": aktif_ariza_sayisi,
    "hat_bazli_arac_durumu": hat_bazli_arac_durumu,
    "arac_ara": arac_ara,
    "verimlilik_hat_bilgisi": verimlilik_hat_bilgisi,
    "guncel_trafik_indeksi": guncel_trafik_indeksi,
    "kaza_ozeti": kaza_ozeti,
    "hat_guzergahi": hat_guzergahi,
    "durak_ara": durak_ara,
    "hat_en_yakin_garaj": hat_en_yakin_garaj,
    "arac_en_yakin_garaj": arac_en_yakin_garaj,
    "hat_planlanan_gercek_karsilastirma": hat_planlanan_gercek_karsilastirma,
    "en_yolcu_yogun_hatlar": en_yolcu_yogun_hatlar,
    "hat_kalkis_saatleri": hat_kalkis_saatleri,
    "otobus_tahmini_varis": otobus_tahmini_varis,
}


def istemci():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


def sohbeti_kaydet(mesaj, cevap):
    """
    Her soru-cevabı private bir GitHub deposuna (iett-sohbet-loglari)
    kaydediyor -- sitede hiçbir yerde görünmüyor, sadece GitHub
    hesabından erişebiliyorsun.
    """
    zaman = datetime.now(ISTANBUL).strftime("%Y-%m-%d %H:%M:%S")
    github_log.kaydet(zaman, mesaj, cevap)


def soru_sor(mesaj, gecmis=None):
    """
    Bir kullanıcı mesajını Claude'a gönderir, gerekirse araçları çalıştırır.
    `gecmis`: önceki tur(lar)dan [{"role": "user"/"assistant", "content": "..."}]
    formatında düz metin geçmişi (opsiyonel) -- "o hat", "o araç" gibi önceki
    cevaba atıflı sorular çalışsın diye. Maliyet kontrolü için çağıran taraf
    bunu son birkaç mesajla sınırlı tutmalı.

    (cevap_metni, harita_hat_kodu) tuple'ı döndürür -- harita_hat_kodu, model bu
    turda hat_guzergahi aracını çağırdıysa o hattın kodu (frontend'in isterse
    haritayı otomatik o hatta odaklaması için), yoksa None.
    """
    client = istemci()
    mesajlar = list(gecmis or []) + [{"role": "user", "content": mesaj}]
    harita_hat_kodu = None

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
            return cevap, harita_hat_kodu

        # Model bir/birden fazla araç çağırmak istiyor -- hepsini çalıştırıp
        # sonuçları "tool_result" olarak modele geri gönderiyoruz.
        mesajlar.append({"role": "assistant", "content": response.content})
        arac_sonuclari = []
        for blok in response.content:
            if blok.type == "tool_use":
                if blok.name == "hat_guzergahi":
                    harita_hat_kodu = blok.input.get("hat_kodu")
                fonksiyon = ARAC_FONKSIYONLARI[blok.name]
                sonuc = fonksiyon(**blok.input)
                arac_sonuclari.append({
                    "type": "tool_result",
                    "tool_use_id": blok.id,
                    "content": sonuc,
                })
        mesajlar.append({"role": "user", "content": arac_sonuclari})
