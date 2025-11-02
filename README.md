# FTC Scrapers Pack (USAA Fraud Project)
Scrapers for:
- **FTC RSS feeds** (press releases and more)
- **Consumer FTC Scams hub** (latest scams items w/ pagination)
- **FTC Legal Library** search results filtered by keyword (e.g., "fraud")

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) RSS — Press Releases (default 20)
python rss_ftc.py --feed press --limit 20 --out data/ftc_rss_press.jsonl

# 2) Consumer Scams hub (20 items from first page)
python consumer_scams.py --limit 20 --out data/ftc_consumer_scams.jsonl

# 3) Legal Library search ("fraud", first 20)
python legal_library_search.py --q fraud --limit 20 --out data/ftc_legal_search_fraud.jsonl
```

All scripts write **JSONL** (one JSON object per line).
