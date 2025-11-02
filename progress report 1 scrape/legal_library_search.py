#!/usr/bin/env python
import argparse, time
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from utils import session, save_jsonl

BASE = "https://www.ftc.gov/legal-library/search?search=fraud"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", default="fraud")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="data/ftc_legal_search.jsonl")
    args = ap.parse_args()

    sess = session()
    url = f"{BASE}?{urlencode({'search': args.q})}"
    r = sess.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    tiles = soup.select("h3 a, .search-results a")
    out = []
    seen = set()
    for a in tiles:
        href = a.get("href")
        if not href:
            continue
        link = href if href.startswith("http") else ("https://www.ftc.gov" + href)
        if link in seen:
            continue
        seen.add(link)
        title = a.get_text(" ", strip=True)
        body = ""
        published = ""
        try:
            ar = sess.get(link)
            ar.raise_for_status()
            psoup = BeautifulSoup(ar.text, "html.parser")
            main = psoup.select_one(".field--name-body") or psoup.find("article") or psoup.body
            paras = [p.get_text(" ", strip=True) for p in (main.find_all("p") if main else [])]
            body = "\n".join([p for p in paras if p])
            dt = psoup.select_one("time[datetime]") or psoup.select_one("time")
            if dt:
                published = dt.get("datetime") or dt.get_text(" ", strip=True)
        except Exception:
            pass

        out.append({"title": title, "url": link, "published": published, "body": body})
        if len(out) >= args.limit:
            break
        time.sleep(0.35)

    save_jsonl(args.out, out)
    print(f"Wrote {len(out)} items to {args.out}")

if __name__ == "__main__":
    main()
