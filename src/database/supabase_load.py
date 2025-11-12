import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
from supabase import create_client, Client
import json
from datetime import datetime
from src.detect import detect_fraud_for_record
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

TABLE = "fraud_articles"

FILE_SOURCES = {
    "ftc_press_releases.jsonl": {"source": "ftc_press", "feed": "press"},
    "ftc_legal_cases.jsonl": {"source": "ftc_legal_cases", "feed": "legal"},
    "ftc_consumer_scams.jsonl": {"source": "ftc_consumer_scams", "feed": "scams"},
    "ftc_data_spotlight.jsonl": {"source": "ftc_data_spotlight", "feed": "data_spotlight"},
    "ftc_legal_search.jsonl": {"source": "ftc_legal_search", "feed": "search_all"},
    "ftc_legal_search_fraud.jsonl": {"source": "ftc_legal_search", "feed": "search_fraud"},
}

def parse_ts(raw):
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%a, %d %b %Y %H:%M:%S %Z",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.isoformat()
        except Exception:
            continue
    return None

def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def normalize_record(rec: dict, source_meta: dict):
    enriched = detect_fraud_for_record(rec, min_hits=2)
    title = (enriched.get("title") or "").strip()
    url = (enriched.get("url") or "").strip()
    body = enriched.get("body") or enriched.get("content") or ""
    return {
        "source": source_meta["source"],
        "feed": source_meta.get("feed"),
        "title": title,
        "url": url,
        "published_at": parse_ts(enriched.get("published")),
        "body": body,
        "is_fraud": bool(enriched.get("is_fraud", False)),
        "fraud_hits": int(enriched.get("fraud_hits", 0)),
        "fraud_score": float(enriched.get("fraud_score", 0.0)),
        "summary": enriched.get("summary"),
    }

def chunked(iterable, size=500):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

def main():
    data_dir = Path("data")
    all_rows = []
    for filename, meta in FILE_SOURCES.items():
        path = data_dir / filename
        if not path.exists():
            print(f"Skipping missing file: {filename}")
            continue
        print(f"Loading {filename} ...")
        for rec in load_jsonl(path):
            row = normalize_record(rec, meta)
            if not row["is_fraud"]:
                continue
            if not row["title"] or not row["url"]:
                continue
            all_rows.append(row)
    print(f"Prepared {len(all_rows)} fraud articles for upsert")
    if not all_rows:
        print("No rows to insert")
        return
    deduped = {}
    for row in all_rows:
        url = row["url"]
        if url in deduped:
            if row["fraud_score"] > deduped[url]["fraud_score"]:
                deduped[url] = row
        else:
            deduped[url] = row
    rows = list(deduped.values())
    print(f"After de-dupe: {len(rows)} unique fraud articles for upsert")
    for batch in chunked(rows, size=500):
        supabase.table(TABLE).upsert(batch, on_conflict="url").execute()
    print("Upsert complete.")

if __name__ == "__main__":
    main()
