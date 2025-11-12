#!/usr/bin/env python
import argparse, time, feedparser
from bs4 import BeautifulSoup
from utils import session, save_jsonl

# Known FTC feed endpoints (from https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds)
FEEDS = {
    "press": "https://www.ftc.gov/feeds/press-release.xml",
    "press_competition": "https://www.ftc.gov/feeds/press-release-competition.xml",
    "press_consumer": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml",
    "business_blog": "https://www.ftc.gov/feeds/blog-business.xml",
    "competition_blog": "https://www.ftc.gov/feeds/blog-competition-matters.xml",
}

def extract_body(sess, url):
    try:
        r = sess.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        container = soup.select_one(".field--name-body") or soup.find("article") or soup.body
        paras = [p.get_text(" ", strip=True) for p in (container.find_all("p") if container else [])]
        return "\n".join([p for p in paras if p])
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default="press", choices=list(FEEDS.keys()))
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="data/ftc_rss.jsonl")
    args = ap.parse_args()

    feed_url = FEEDS[args.feed]
    fd = feedparser.parse(feed_url)
    sess = session()
    out = []
    for e in fd.entries[:args.limit]:
        url = e.link
        title = e.title
        published = getattr(e, "published", None)
        body = extract_body(sess, url)
        out.append({"source": args.feed, "title": title, "url": url, "published": published, "body": body})
        time.sleep(0.35)
    save_jsonl(args.out, out)
    print(f"Wrote {len(out)} items to {args.out}")

if __name__ == "__main__":
    main()
