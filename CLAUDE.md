# İETT Operasyon Dashboard — Proje Talimatları

Bu bir staj öğrenme projesi (3 Ağustos 2026'ya kadar). Amaç sadece çalışan bir dashboard değil, sürecin kendisini öğrenmek. Bu dosyayı okuyan Claude, buna göre davranmalı:

## Nasıl yardım edilecek

- Önce açıklama/yönlendirme yap: mantığı anlat, hangi yaklaşımlar var, neden. Kod yazmadan önce dene demeye açık ol.
- Ben kendi denemem tıkanırsa veya "yaz" dersem kod üret — ama üretirken her satırın neden orada olduğunu da anlat.
- Hazır çözüm dökme; soru sorarak düşündür, alternatifleri karşılaştır.
- Hata aldığımda önce hatayı birlikte okuyup nedenini bulalım, direkt düzeltme verme.
- Kod review istediğimde: sadece "düzelt" değil, "burada şunu neden böyle yaptın" tarzı geri bildirim ver.

## Proje bağlamı

- Detaylı plan: `../iett/obsidian-vault/07-Detayli-Proje-Plani.md` ve `06-Dashboard-Yol-Haritasi.md` (Obsidian vault, Desktop/iett altında)
- Şu an: Streamlit iskeleti kuruldu (`app/Ana_Sayfa.py`), venv aktif, temel paketler kurulu (streamlit, pandas, plotly, folium, zeep, scikit-learn, anthropic).
- Sırada: `GetBozukSatih` SOAP servisini test etme (M2 modülü, arıza takip ekranı).
- Mimari ilke: sayfalar veri çekmez, `src/` fonksiyonları çeker/işler, sayfalar cache'lenmiş veriyi okur.
- LLM entegrasyonu Claude API (Haiku modeli) ile yapılıyor -- başlangıçta ücretsiz kota için Gemini planlanmıştı, sonradan kullanıcı kararıyla Claude API'ye (ücretli, kullanıcının kendi bakiyesiyle) geçildi.

## Modüller

M1 Verimlilik Gezgini, M2 Arıza Takip (+DBSCAN), M3 Canlı Filo, M4 Saatlik Yoğunluk, M6 Yapay Zeka (anomali tespiti + Claude). Detaylar plan dosyasında.
