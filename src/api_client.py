"""İETT SOAP servisleri için ortak yardımcı fonksiyonlar."""
import time
import json
import re
import xml.etree.ElementTree as ET

import requests

BASE = "https://api.ibb.gov.tr/iett"
NS = "http://tempuri.org/"


def soap_call(path, method, params, timeout=30, max_retries=3):
    """Bir İETT SOAP metodunu çağırır, ham XML metnini döndürür."""
    body = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f'<soap:Body><{method} xmlns="{NS}">{body}</{method}></soap:Body></soap:Envelope>'
    )
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f"{NS}{method}",
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            r = requests.post(f"{BASE}/{path}", data=envelope.encode("utf-8"), headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            last_err = e
            time.sleep(1 + attempt)
    raise last_err


def extract_json_result(xml_text, method):
    """<Get..._jsonResult> içindeki JSON string'ini ayıklar ve parse eder."""
    root = ET.fromstring(xml_text)
    tag = f"{method}Result"
    el = next((e for e in root.iter() if e.tag.endswith(tag)), None)
    if el is None or el.text is None:
        return []
    return json.loads(el.text)


def parse_dotnet_date(s):
    """'/Date(1717255920000)/' formatını epoch saniyeye çevirir."""
    if not isinstance(s, str):
        return None
    m = re.search(r"/Date\((\d+)\)/", s)
    return int(m.group(1)) / 1000 if m else None


def call_json(path, method, params, timeout=30, max_retries=3):
    """soap_call + extract_json_result kısayolu."""
    xml_text = soap_call(path, method, params, timeout=timeout, max_retries=max_retries)
    return extract_json_result(xml_text, method)
