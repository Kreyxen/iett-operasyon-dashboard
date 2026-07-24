# data/raw içindeki dosyaların kaynağı

- **trafik_indeksi_raw.json** — data.ibb.gov.tr CKAN API'sinden `src/01_ham_veri_cek.py` ile
  çekildi. Tam anlamıyla ham: API'nin döndürdüğü hiçbir alan değiştirilmedi.

- **gorev_2024-06-03.parquet** — İETT'nin `GetIettArsivGorev_json` servisinden (SOAP API)
  3 Haziran 2024 için çekilmiş, araç bazında gerçekleşen/planlanan sefer kayıtları.
  Tam anlamıyla ham: her satır tek bir seferi temsil ediyor, hiçbir özetleme yapılmadı.

- **belbim_ozet_202406.parquet** — ⚠️ Tam anlamıyla ham DEĞİL. Kaynağı BELBİM'in Haziran 2024
  saatlik kart geçiş verisi (data.ibb.gov.tr, "Hourly Public Transport Data Set"), ama o dosya
  tek başına 1,6 GB olduğu için önceki bir çalışmada zaten hat+saat+ilçe bazında özetlenmişti.
  Burada o özet halini kullanıyoruz. Gerçek bir projede bunu "bronze/silver katman" ayrımı
  olarak düşünebilirsin: bronze = tamamen ham, silver = hafif özetlenmiş ama hâlâ ayrıntılı.
