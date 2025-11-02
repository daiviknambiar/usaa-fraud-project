import os, json, requests

UA = {"User-Agent": "USAA-Fraud-News/1.0 (+student project)"}

def session(timeout=15):
    s = requests.Session()
    s.headers.update(UA)
    _orig = s.request
    def _request(method, url, **kw):
        kw.setdefault("timeout", timeout)
        return _orig(method, url, **kw)
    s.request = _request
    return s

def save_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
