#!/usr/bin/env python
"""
Scraper for FTC Press Releases related to fraud/scams
"""
import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import argparse
import time
from bs4 import BeautifulSoup
from src.utils import session, save_jsonl, is_fraud

BASE = "https://www.ftc.gov/news-events/news/press-releases"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="data/ftc_press_releases.jsonl")
    ap.add_argument("--pages", type=int, default=3, help="Number of listing pages to scrape")
    args = ap.parse_args()
    
    sess = session()
    out = []
    
    # Scrape multiple pages of press releases
    for page_num in range(args.pages):
        page_url = f"{BASE}?page={page_num}" if page_num > 0 else BASE
        print(f"Fetching page {page_num + 1}...")
        
        try:
            r = sess.get(page_url)
            r.raise_for_status()
        except Exception as e:
            print(f"Error fetching page {page_num}: {e}")
            break
            
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Find all press release links
        # FTC uses article tags with links inside
        articles = soup.select("article h3 a, article h2 a")
        
        if not articles:
            print(f"No articles found on page {page_num + 1}")
            break
        
        for a in articles:
            if len(out) >= args.limit:
                break
                
            href = a.get("href")
            if not href or href.startswith("#"):
                continue
                
            url = href if href.startswith("http") else ("https://www.ftc.gov" + href)
            title = a.get_text(strip=True)
            
            # Check if title indicates fraud/scam content
            if not is_fraud(title):
                continue
            
            print(f"Scraping: {title}")
            
            body = ""
            pub = ""
            
            try:
                ar = sess.get(url)
                ar.raise_for_status()
                asoup = BeautifulSoup(ar.text, "html.parser")
                
                # Extract publication date
                dt = asoup.select_one("time[datetime]") or asoup.select_one(".date")
                if dt:
                    pub = dt.get("datetime") or dt.get_text(strip=True)
                
                # Extract main content
                # FTC press releases use specific content areas
                main = (asoup.select_one("article.node--press-release") or 
                       asoup.select_one(".region-content") or
                       asoup.select_one("main") or 
                       asoup.body)
                
                if main:
                    # Get all paragraphs
                    paras = []
                    for p in main.find_all("p"):
                        text = p.get_text(" ", strip=True)
                        if text and len(text) > 20:  # Filter out very short paragraphs
                            paras.append(text)
                    body = "\n\n".join(paras)
                
                time.sleep(0.5)  # Be polite to the server
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
            
            out.append({
                "title": title,
                "url": url,
                "published": pub,
                "body": body,
                "source": "FTC Press Releases"
            })
            
        if len(out) >= args.limit:
            break
    
    save_jsonl(args.out, out)
    print(f"\nWrote {len(out)} fraud-related press releases to {args.out}")

if __name__ == "__main__":
    main()