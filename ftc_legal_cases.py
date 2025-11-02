#!/usr/bin/env python
"""
Scraper for FTC Legal Library Cases related to fraud/scams
"""
import argparse
import time
from bs4 import BeautifulSoup
from utils import session, save_jsonl
from keywords import is_fraud

# Specific case URLs you want to scrape
CASE_URLS = [
    "https://www.ftc.gov/legal-library/browse/cases-proceedings/172-3013-match-group-inc",
    "https://www.ftc.gov/legal-library/browse/cases-proceedings/x240032-fba-machinepassive-scaling-ftc-v",
    "https://www.ftc.gov/legal-library/browse/cases-proceedings/142-3255-x150061-roca-labs-inc"
]

BASE = "https://www.ftc.gov/legal-library/browse/cases-proceedings"

def scrape_case(sess, url):
    """Scrape a single legal case page"""
    try:
        r = sess.get(url)
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Extract title
    title_elem = soup.select_one("h1") or soup.select_one(".page-title")
    title = title_elem.get_text(strip=True) if title_elem else "No title"
    
    # Extract date
    pub = ""
    date_elem = soup.select_one("time[datetime]") or soup.select_one(".date")
    if date_elem:
        pub = date_elem.get("datetime") or date_elem.get_text(strip=True)
    
    # Extract main content
    body_parts = []
    
    # Look for case description/overview
    overview = soup.select_one(".case-overview") or soup.select_one(".field--name-field-case-overview")
    if overview:
        for p in overview.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text and len(text) > 20:
                body_parts.append(text)
    
    # Get main content area
    main = soup.select_one("article") or soup.select_one(".region-content") or soup.select_one("main")
    if main:
        for p in main.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text and len(text) > 20 and text not in body_parts:
                body_parts.append(text)
    
    body = "\n\n".join(body_parts)
    
    return {
        "title": title,
        "url": url,
        "published": pub,
        "body": body,
        "source": "FTC Legal Library"
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="data/ftc_legal_cases.jsonl")
    ap.add_argument("--specific-only", action="store_true", 
                    help="Only scrape the specific case URLs listed in the script")
    args = ap.parse_args()
    
    sess = session()
    out = []
    
    if args.specific_only:
        # Just scrape the specific URLs you listed
        print(f"Scraping {len(CASE_URLS)} specific cases...")
        for url in CASE_URLS:
            print(f"Scraping: {url}")
            case_data = scrape_case(sess, url)
            if case_data:
                out.append(case_data)
            time.sleep(0.5)
    else:
        # Try to scrape from the browse page
        print("Fetching cases from legal library...")
        try:
            r = sess.get(BASE)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Find case links
            case_links = soup.select("article h3 a, article h2 a, .views-row h3 a")
            
            for a in case_links:
                if len(out) >= args.limit:
                    break
                
                href = a.get("href")
                if not href:
                    continue
                
                url = href if href.startswith("http") else ("https://www.ftc.gov" + href)
                title = a.get_text(strip=True)
                
                # Filter for fraud-related cases
                if not is_fraud(title):
                    continue
                
                print(f"Scraping: {title}")
                case_data = scrape_case(sess, url)
                if case_data:
                    out.append(case_data)
                
                time.sleep(0.5)
        
        except Exception as e:
            print(f"Error fetching case list: {e}")
            print("Falling back to specific case URLs...")
            for url in CASE_URLS:
                print(f"Scraping: {url}")
                case_data = scrape_case(sess, url)
                if case_data:
                    out.append(case_data)
                time.sleep(0.5)
    
    save_jsonl(args.out, out)
    print(f"\nWrote {len(out)} legal cases to {args.out}")

if __name__ == "__main__":
    main()