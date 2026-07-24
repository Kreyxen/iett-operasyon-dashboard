# İBB Açık Veri — Ulaşım Veri Envanteri (Doğrulanmış)

Tarama tarihi: 2026-07-08. Kaynaklar: data.ibb.gov.tr CKAN API (package_show + datastore_search, canlı sorgulandı) + `Desktop\iett` klasöründeki önceki proje notları/örnek veriler.

> Not: CKAN datastore satır sayıları bazı büyük dosyalarda 1.048.575'te kesiliyor (önizleme limiti); gerçek dosya daha büyük. BELBİM saatlik verinin datastore önizlemesi boş dönüyor ama CSV dosyaları indirilebilir durumda.

## A) Talep / Yolcu Verileri (projenin kalbi)

| Veri Seti | Kolonlar | Tarih Aralığı | Boyut/Satır | Statik? |
|---|---|---|---|---|
| **Hourly Public Transport Data Set (BELBİM)** ⭐ | transition_date, transition_hour, transport_type_id, road_type, line, transfer_type, number_of_passage, number_of_passenger, product_kind, transaction_type_desc, town, line_name, station_poi_desc_cd | Oca 2020 – Ara 2024 (aylık 60 CSV) | Ay başına 0.35–1.65 GB (~milyonlarca satır/ay) | **Statik** (Nis 2025'te donduruldu) |
| GetIettYolculukHat_json (SOAP API) | hat, yolcu sayısı (top-50 hat/gün) | Tarih parametreli, geçmişe döngüyle gidilebilir | 50 satır/gün | **Canlı API** |
| İstanbulkart Harici Geçiş | small_date, Operator_Grubu, Operator, Kart_Tipi, yolculuk_sayisi, yolcu_sayisi | 2023–2025 (günlük) | 48.831 satır (2025) | Yıllık güncelleniyor |
| Elektronik Bilet Geçişleri | Yil, KullanAt/İstanbulkart/QR geçiş+kişi adetleri | Yıllık | 12 satır | Statik denecek kadar küçük |
| Yolculuk Türü Bazında Yolcu Sayısı | Yil, Yolcu Sayisi (Kisi/Gun), Yolculuk Turu | ~2019'a kadar yıllık | 24 satır | Statik |

## B) Ağ / Sefer Planı Verileri (statik omurga)

| Veri Seti | Kolonlar | Kapsam | Satır | Statik? |
|---|---|---|---|---|
| **İETT GTFS** ⭐ | routes(7), trips(5), stop_times(6: trip_id, stop_id, stop_sequence, arrival/departure_time, timepoint), stops, calendar | Son güncelleme **17 Mart 2026** — sanılandan taze | routes 9.279 · trips 135.625 · stop_times ≥1.05M (kesik) | Ara ara güncelleniyor |
| iett_guzergah.csv (yerel, SOAP'tan çekilmiş) | HATKODU, YON, SIRANO, DURAKKODU, DURAKADI, boylam, enlem, DURAKTIPI, ISLETMEBOLGE, ILCEADI, SHATADI, TARIFE, HAT_UZUNLUGU, SEFER_SURESI | 792 hat, 62.091 durak kaydı | 62k | Statik (yerelde hazır) |
| Public Transport GTFS (diğer operatörler: Metro, Marmaray, Şehir Hatları, minibüs, İDO…) | standart GTFS + frequencies(headway_secs!) | 8 operatör | 499 hat · 7.073 durak · 14.389 trip · frequencies 2.310 | Statik (Mar 2024) |
| Planlanan Sefer Saati (SOAP) | hat, gün tipi, ana durak kalkış saatleri | güncel plan | — | Canlı API |
| Metro İstanbul Sefer Tarifeleri | API | güncel | — | Canlı API |

## C) Operasyon / Filo (İETT SOAP API — api.ibb.gov.tr/iett)

| Servis | İçerik | Not |
|---|---|---|
| GetFiloAracKonum_json | Anlık tüm filo konumu: operatör, garaj, kapı no, saat, koordinat, hız, plaka | Sadece "şu an", geçmiş yok |
| GetIettArsivGorev_json | Araç bazında hat, güzergah, görev başlama/bitiş (epoch) | Tarih parametreli → geçmiş toplanabilir, TEST EDİLDİ çalışıyor |
| Sefer Gerçekleşme | Planlanan vs gerçekleşen sefer | Saatte 100 istek limiti |
| GetKazaLokasyon | KAZASAAT, BOYLAM, ENLEM (hat/plaka YOK) | Tarih parametreli |
| GetBozukSatih | Şoför bildirimli bozuk yol + koordinat | Canlı |
| GetAkarYakitToplamLitre | — | ⚠️ ÖLÜ SERVİS, boş dönüyor |

## D) Trafik / Dış Değişkenler

| Veri Seti | Kolonlar | Tarih Aralığı | Satır | Statik? |
|---|---|---|---|---|
| **Hourly Traffic Density** ⭐ | DATE_TIME, LATITUDE, LONGITUDE, GEOHASH, MIN/MAX/AVERAGE_SPEED, NUMBER_OF_VEHICLES | Oca 2020 – Oca 2025 (61 aylık CSV) | ~1.76M satır/ay, ~110–135 MB/ay | Statik |
| İstanbul Trafik İndeksi | trafficindexdate, min/max/average_traffic_index | ~2015 – Eyl 2025 (günlük) | 3.332 | Güncelleniyor + canlı API var |
| Günlük Araç Sayımı | Tarih, Sensor Adi/No, X/Y Koordinati, ARAC TOPLAM | 2016–2024 | 73.571 satır (2024) | Yıllık dosyalar |
| Ölümlü/Yaralanmalı Kaza Sayısı | Yil, TR/IST yerleşim içi-dışı | 13 yıl | 13 | Yıllık |
| UKOME Ana Arterler | road_name, road_type, number_of_lanes, pavement_type, shape (geometri) | güncel | 40.616 yol parçası | Statik |
| Görüntü İşleme Araç Verisi | start_time, camera_id, class_id1-5, direction, intersection, total, occupancy, speed_mean | kısa dönem | 228 (çok küçük) | Statik |
| Sinyalize Kavşak | API + PDF doküman | güncel | — | Canlı API |

## E) Bağlam / Sosyoekonomik

| Veri Seti | Kolonlar | Satır | Not |
|---|---|---|---|
| Ulaşım Talep Tahmin Modeli (2020 kalibre, 2040 projeksiyon) | 16 kaynak: karayolu ağı, toplu taşıma ağı/şebeke (XLSX+KMZ), 540 analiz bölgesi | — | Şub 2026'da güncellendi |
| Nüfus Projeksiyonu | Sayim Yili, Varsayim 1-6 | 21 (2050'ye kadar) | Statik |
| VDYM Araç Sahipliği | İlçe × araç tipi Var/Yok oranları | 39 ilçe | Statik |
| Yükseköğrenim Yurt Konumları | ILCE, Merkez Adi, Lat, Lon | 16 | Mar 2026 güncel |
| İnşaat Aşamasındaki Yol Çalışmaları | ilçe bazlı XLSX | küçük | Nis 2026 güncel |

## Yerelde Hazır İşlenmiş Veriler (önceki projeden — Desktop\iett\data\islenmis)

- hat_verimlilik_haziran2024 / aralik2024 (temiz) — hat bazlı verimlilik skorları
- hat_km_haziran2024, hat_uzunluk, gunluk_hat_km — hat bazlı km üretimi
- hat_segmentleri (+capraz, +guvenilir) — hat segmentasyon modeli çıktıları
- haziran_aralik_karsilastirma — iki dönem karşılaştırması

## Kritik Tespitler

1. **BELBİM saatlik veri Ara 2024'te bitiyor ve artık güncellenmiyor** → gerçek zamanlı değil, tarihsel analiz/model eğitimi verisi olarak kullanılmalı.
2. **İETT GTFS Mart 2026'da güncellenmiş** (eski not "donduruldu" diyordu — düzeltildi). Güncel sefer planı için en iyi kaynak.
3. Talep (BELBİM) + trafik yoğunluğu (geohash) + GTFS planı aynı 2020–2024 dönemini kapsıyor → birleştirilebilir.
4. Durak bazlı biniş verisi otobüste YOK (araç içi validatör) → analizler hat+ilçe+saat çözünürlüğünde.
5. Kaza verisi sadece koordinat+saat; hat eşleştirme GetIettArsivGorev ile zaman-mekân çakıştırmasıyla mümkün.
