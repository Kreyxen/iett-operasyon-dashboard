"""
DERS 16: Ortak görsel tema (CSS enjeksiyonu)

Streamlit'in kendi sayfa yapısını (sidebar + içerik) yeniden inşa
etmiyoruz -- bu kırılgan ve gereksiz olurdu. Bunun yerine mevcut
yapının üzerine hedefli CSS uyguluyoruz: yazı tipi, metrik sayıların
görünümü (İETT'nin split-flap durak tabelalarına gönderme -- sabit
genişlikli, hafif vurgulu rakamlar), kenarlıklar, başlık çizgileri.

Her sayfa, en üstte `tema.uygula()` çağırarak bunu içeri alıyor
(tekrarlı ama basit -- Streamlit'in çoklu sayfa yapısında ortak bir
"layout" dosyası yok, her sayfa bağımsız çalışıyor).
"""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Başlıklar: biraz daha sık aralıklı, teknik/tabela hissi */
h1, h2, h3 {
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600;
    letter-spacing: -0.01em;
}

h1 {
    border-bottom: 2px solid #3987E5;
    padding-bottom: 0.4rem;
}

/* Metrikler: split-flap durak tabelası hissi -- mono, sabit genişlik, amber */
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    color: #D9A441;
    font-weight: 600;
}

[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Sans', sans-serif;
    color: #9C9A93;
}

/* Kenarlıklı container'lar (st.container(border=True)) -- biraz daha belirgin */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 8px;
}

/* Sidebar: kontrol paneli hissi */
[data-testid="stSidebar"] {
    border-right: 1px solid #2A2E3A;
}

/* Butonlar: hafif yuvarlatılmış, mono etiket (hazır sorular vb. için) */
.stButton button {
    border-radius: 6px;
}

/* Caption/açıklama metinleri biraz daha okunaklı */
[data-testid="stCaptionContainer"] {
    color: #9C9A93;
}
</style>
"""


def uygula():
    st.markdown(CSS, unsafe_allow_html=True)
