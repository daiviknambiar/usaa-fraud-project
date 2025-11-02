import re
from typing import Iterable, List, Tuple

FRAUD_TERMS: List[str] = [
    "fraud", "scam", "scams", "scammer", "scammers",
    "phishing", 
    "identity theft", "identity fraud"
]

PATTERNS: List[re.Pattern] = [
    re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE) for term in FRAUD_TERMS
]

def find_hits(text: str) -> List[Tuple[str, Tuple[int, int]]]:
    """Return [(term, (start, end)), ...] for each match."""
    if not text:
        return []
    hits: List[Tuple[str, Tuple[int, int]]] = []
    for term, pat in zip(FRAUD_TERMS, PATTERNS):
        for m in pat.finditer(text):
            hits.append((term, (m.start(), m.end())))
    return hits

def is_fraud(text: str, *, min_hits: int = 1) -> bool:
    """True if text contains >= min_hits fraud-related terms."""
    return len(find_hits(text)) >= min_hits
