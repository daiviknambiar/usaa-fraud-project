import re

KEYWORDS = [
    "fraud", "frauds", "scam", "scams", "scheme", "schemes",
    "phishing", "smishing", "vishing",
    "identity theft", "id theft",
    "imposter", "impersonation",
    "business email compromise", "bec",
    "investment scam", "investment fraud",
    "account takeover",
    "money mule", "money mules",
    "skimming", "carding",
    "check fraud", "wire fraud",
    "refund scam", "refund fraud",
    "crypto scam", "cryptocurrency scam", "ransomware"
]

def count_hits(text: str) -> int:
    if not text:
        return 0
    t = text.lower()
    hits = 0
    for kw in KEYWORDS:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        hits += len(re.findall(pattern, t))
    return hits

def detect_fraud_for_record(rec: dict, min_hits: int = 2):
    title = (rec.get("title") or "").strip()
    body = (rec.get("body") or "").strip()
    text = f"{title}\n{body}"
    hits = count_hits(text)
    is_fraud = hits >= min_hits
    return {
        **rec,
        "is_fraud": is_fraud,
        "fraud_hits": hits,
        "fraud_score": float(hits),
    }
