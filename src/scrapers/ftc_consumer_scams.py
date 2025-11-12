#!/usr/bin/env python
import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import argparse
import time
from bs4 import BeautifulSoup
from src.utils import session, save_jsonl

BASE = "https://consumer.ftc.gov/scams"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="data/ftc_consumer_scams.jsonl")
    args = ap.parse_args()

    sess = session()
    r = sess.get(BASE)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.select("h3 a")
    out = []
    for a in cards:
        href = a.get("href")
        if not href or href.startswith("#"):
            continue
        url = href if href.startswith("http") else ("https://consumer.ftc.gov" + href)
        body = ""
        pub = ""
        try:
            ar = sess.get(url)
            ar.raise_for_status()
            asoup = BeautifulSoup(ar.text, "html.parser")
            main = asoup.select_one("main") or asoup.select_one("article") or asoup.body
            if main:
                paras = [p.get_text(" ", strip=True) for p in main.find_all("p")]
                body = "\n".join([p for p in paras if p])
            dt = asoup.select_one("time[datetime]") or asoup.select_one("time")
            if dt:
                pub = dt.get("datetime") or dt.get_text(" ", strip=True)
        except Exception:
            pass
        out.append({"title": a.get_text(strip=True), "url": url, "published": pub, "body": body})
        if len(out) >= args.limit:
            break
        time.sleep(0.35)

    save_jsonl(args.out, out)
    print(f"Wrote {len(out)} items to {args.out}")

if __name__ == "__main__":
    main()
