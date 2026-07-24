"""
DERS 15: Sohbet kayıtlarını ayrı, PRIVATE bir GitHub deposuna yazmak

Neden ayrı bir depo? Asıl proje deposu (iett-operasyon-dashboard) PUBLIC
-- mentöre/arkadaşlara gösterebilmek için. Ama sohbet logları kişisel
bilgi içerebilir (kim ne sordu), bu yüzden ayrı, PRIVATE bir depoya
(iett-sohbet-loglari) yazıyoruz -- sadece sen (GitHub hesabınla)
görebiliyorsun.

Streamlit Cloud sadece asıl proje deposunu izlediği için, bu ayrı
depoya yazmak deploy tetiklemiyor -- dal (branch) numarası yapmaya
gerek kalmadı, doğrudan `main`'i kullanabiliyoruz.

GitHub'ın Contents API'sini kullanıyoruz (git komutu değil, düz HTTP
istekleri) -- Streamlit Cloud'un dosya sistemi kalıcı olmadığı için
yerel bir git deposu tutup commit atmak güvenilir olmazdı.
"""
import base64

import requests
import streamlit as st

LOG_REPO = "Kreyxen/iett-sohbet-loglari"
DAL = "main"
DOSYA_YOLU = "sohbet_gecmisi.md"
API_KOK = f"https://api.github.com/repos/{LOG_REPO}"


def _basliklar():
    return {
        "Authorization": f"token {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }


def kaydet(zaman, soru, cevap):
    """Bir soru-cevabı private log deposundaki dosyaya ekler (satır olarak)."""
    r = requests.get(
        f"{API_KOK}/contents/{DOSYA_YOLU}", headers=_basliklar(),
        params={"ref": DAL}, timeout=15,
    )
    if r.status_code == 200:
        mevcut = base64.b64decode(r.json()["content"]).decode("utf-8")
        sha = r.json()["sha"]
    else:
        mevcut = "# Sohbet Geçmişi\n\n"
        sha = None

    yeni_satir = f"\n**{zaman}**\n- Soru: {soru}\n- Cevap: {cevap}\n"
    guncel_icerik = mevcut + yeni_satir

    veri = {
        "message": f"Sohbet kaydı: {zaman}",
        "content": base64.b64encode(guncel_icerik.encode("utf-8")).decode("utf-8"),
        "branch": DAL,
    }
    if sha:
        veri["sha"] = sha

    requests.put(f"{API_KOK}/contents/{DOSYA_YOLU}", headers=_basliklar(), json=veri, timeout=15)


def oku():
    """Log dosyasının tam içeriğini (markdown metni) döndürür."""
    r = requests.get(
        f"{API_KOK}/contents/{DOSYA_YOLU}", headers=_basliklar(),
        params={"ref": DAL}, timeout=15,
    )
    if r.status_code != 200:
        return "Henüz hiç soru sorulmamış."
    return base64.b64decode(r.json()["content"]).decode("utf-8")
