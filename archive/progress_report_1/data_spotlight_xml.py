import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime

FEED_URL = "https://www.ftc.gov/feeds/data-spotlight.xml"
OUT_PATH = "data/ftc_data_spotlight.jsonl"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ftc-scrapers/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def t(el): return (el.text or "").strip() if el is not None else ""

def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    if root.tag.endswith("feed"):
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in root.findall("a:entry", ns):
            title = t(e.find("a:title", ns))
            link = ""
            for ln in e.findall("a:link", ns):
                href = ln.attrib.get("href", "")
                if not link: link = href
                if ln.attrib.get("rel") in (None, "alternate"): link = href
            published = t(e.find("a:published", ns)) or t(e.find("a:updated", ns))
            summary = t(e.find("a:summary", ns)) or t(e.find("a:content", ns))
            yield {
                "title": title, "link": link, "published": published, "summary": summary,
                "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source": "data-spotlight",
            }
        return
    for it in root.findall(".//item"):
        title = t(it.find("title"))
        link = t(it.find("link"))
        pub = t(it.find("pubDate"))
        desc = t(it.find("description"))
        yield {
            "title": title, "link": link, "published": pub, "summary": desc,
            "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source": "data-spotlight",
        }

def main():
    xml_bytes = fetch(FEED_URL)
    items = list(parse(xml_bytes))
    os.makedirs("data", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for row in items:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(items)} → {OUT_PATH}")

if __name__ == "__main__":
    import os; main()
