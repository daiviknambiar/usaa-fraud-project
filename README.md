# FTC Fraud Scrapers

A collection of web scrapers that collect fraud-related content from Federal Trade Commission (FTC) websites, perform keyword-based fraud detection, and load results into a Supabase database.

## Project Structure

```
https://github.com/daiviknambiar/usaa-fraud-project/blob/ae3ccec77f639a8687f070cfb5c45af43f28a4a2/Screenshot%202025-11-30%20at%2011.12.15%20PM.jpg
```

## Setup

1. **Create and activate virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
Create a `.env` file with your Supabase credentials:
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Usage

### Quick Start (Recommended)

Use the main entry point for all operations:

```bash
# Run a specific scraper
.venv/bin/python main.py scrape press --limit 20 --pages 3
.venv/bin/python main.py scrape legal --specific-only
.venv/bin/python main.py scrape scams --limit 30

# Load data to Supabase
.venv/bin/python main.py load

# Run full pipeline (all scrapers + load to database)
.venv/bin/python main.py all

# Show help
.venv/bin/python main.py --help
```

### Running Individual Scrapers Directly

You can also run scrapers directly if needed:

```bash
# FTC Press Releases (with pagination)
.venv/bin/python src/scrapers/ftc_press_releases.py --limit 20 --pages 3

# FTC Legal Cases
.venv/bin/python src/scrapers/ftc_legal_cases.py --limit 20
.venv/bin/python src/scrapers/ftc_legal_cases.py --specific-only

# FTC Consumer Scams
.venv/bin/python src/scrapers/ftc_consumer_scams.py --limit 30
```

### Using Helper Scripts

Alternative helper scripts are available in `src/scripts/`:

```bash
# Run a specific scraper
.venv/bin/python src/scripts/run_scraper.py press --limit 20 --pages 3

# Run all scrapers
.venv/bin/python src/scripts/run_all_scrapers.py
```

### Loading Data to Supabase

```bash
# Via main.py (recommended)
.venv/bin/python main.py load

# Or directly
.venv/bin/python src/database/supabase_load.py
```

The loader will:
- Read all JSONL files from the `data/` directory
- Apply fraud detection scoring
- Deduplicate records by URL
- Filter for fraud-related content (min 2 keyword hits)
- Upsert to the `fraud_articles` table

## How It Works

### 1. Data Collection (Scrapers)

Each scraper extracts:
- **title**: Article/case title
- **url**: Source URL
- **published**: Publication date
- **body**: Full content text
- **source**: Identifies the data source

Scrapers use keyword filtering ([src/utils/keywords.py](src/utils/keywords.py)) during collection to focus on fraud-related content.

### 2. Fraud Detection (Two-Tier System)

**Tier 1: Content Filtering** ([src/utils/keywords.py](src/utils/keywords.py))
- Basic filtering during scraping
- Simple fraud terms: "fraud", "scam", "phishing", "identity theft"
- Minimum 1 hit required

**Tier 2: Classification** ([src/detect/fraud_detector.py](src/detect/fraud_detector.py))
- Applied during database loading
- Extended 16+ keyword list including: ransomware, money mules, business email compromise, etc.
- Minimum 2 hits required for classification
- Adds `is_fraud`, `fraud_hits`, and `fraud_score` fields

### 3. Database Loading

[src/database/supabase_load.py](src/database/supabase_load.py) performs:
- Record normalization across different scraper formats
- Multi-format date parsing
- URL-based deduplication (keeps highest fraud score)
- Batch upserts (500 records per batch)
- Fraud-only filtering

## Output Format

Scraped data is stored as JSONL (JSON Lines) in the `data/` directory:

```json
{
  "title": "FTC Takes Action Against Scam Operation",
  "url": "https://www.ftc.gov/...",
  "published": "2024-11-02",
  "body": "Full article text...",
  "source": "FTC Press Releases"
}
```

After fraud detection:
```json
{
  "title": "FTC Takes Action Against Scam Operation",
  "url": "https://www.ftc.gov/...",
  "published_at": "2024-11-02T00:00:00",
  "body": "Full article text...",
  "source": "ftc_press",
  "feed": "press",
  "is_fraud": true,
  "fraud_hits": 5,
  "fraud_score": 5.0
}
```

## Development

### Adding a New Scraper

1. Create a new file in `src/scrapers/`
2. Add the path setup at the top:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```
3. Import utilities: `from src.utils import session, save_jsonl, is_fraud`
4. Follow the existing scraper patterns
5. Add to `main.py` SCRAPERS dict

### Testing

Test individual scrapers with small limits:
```bash
# Via main.py
.venv/bin/python main.py scrape press --limit 2

# Or directly
.venv/bin/python src/scrapers/ftc_press_releases.py --limit 2
```

### Legacy Code

The `archive/progress_report_1/` directory contains earlier scraper versions that have been superseded by the current implementation.

## License

This is a student project for USAA fraud detection research.
