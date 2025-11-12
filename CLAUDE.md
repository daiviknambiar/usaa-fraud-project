# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a USAA fraud detection project that scrapes FTC (Federal Trade Commission) websites for fraud-related content, performs keyword-based fraud detection, and loads the results into a Supabase database.

## Project Structure

```
ftc-scrapers/
├── main.py             # Main entry point - use this!
├── src/                # All source code
│   ├── scrapers/       # Individual FTC website scrapers
│   ├── detect/         # Fraud detection logic
│   ├── database/       # Database loading scripts
│   ├── utils/          # Shared utilities (HTTP, keywords)
│   └── scripts/        # Helper scripts
├── data/               # Output data (JSONL files)
├── archive/            # Legacy code (archived)
└── tests/              # Tests (future)
```

## Setup and Environment

### Dependencies Installation
```bash
pip install -r requirements.txt
```

Key dependencies: `beautifulsoup4`, `feedparser`, `requests`, `lxml`, `supabase`, `python-dotenv`

### Environment Variables
Create a `.env` file with:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key for database access

### Virtual Environment
Always use the virtual environment when running scripts:
```bash
.venv/bin/python <script>
```

## Running Scrapers

### Primary Method: main.py (Recommended)
All operations should go through `main.py`:

```bash
# Run a specific scraper
.venv/bin/python main.py scrape press --limit 20 --pages 3
.venv/bin/python main.py scrape legal --specific-only
.venv/bin/python main.py scrape scams --limit 30

# Load data to Supabase
.venv/bin/python main.py load

# Run full pipeline (all scrapers + load)
.venv/bin/python main.py all

# Show help
.venv/bin/python main.py --help
```

### Direct Scraper Execution
Scrapers can be run directly if needed:

```bash
# All scrapers are in src/scrapers/
.venv/bin/python src/scrapers/ftc_press_releases.py --limit 20 --pages 3
.venv/bin/python src/scrapers/ftc_legal_cases.py --limit 20
.venv/bin/python src/scrapers/ftc_consumer_scams.py --limit 20
```

## Data Processing Pipeline

The complete fraud detection pipeline:
1. **Scraping**: Scrapers in `src/scrapers/` collect data from FTC sources
2. **Fraud Detection**: [src/detect/fraud_detector.py](src/detect/fraud_detector.py) applies keyword matching
3. **Database Loading**: [src/database/supabase_load.py](src/database/supabase_load.py) processes JSONL files and uploads to Supabase

### Running the Full Pipeline
```bash
# Recommended: Run everything via main.py
.venv/bin/python main.py all

# Or step by step:
# 1. Run all scrapers
.venv/bin/python main.py scrape press --limit 20 --pages 3
.venv/bin/python main.py scrape legal --limit 20
.venv/bin/python main.py scrape scams --limit 20

# 2. Load to database
.venv/bin/python main.py load
```

## Architecture

### Scraper Architecture
All scrapers follow a common pattern:
- Located in `src/scrapers/` directory
- Use `sys.path.insert(0, str(Path(__file__).parent.parent.parent))` at top to add project root to path
- Import from `src.utils`: `session()` for HTTP requests, `save_jsonl()` for output, `is_fraud()` for filtering
- All imports use the `src.` prefix (e.g., `from src.utils import session`)

Each scraper extracts:
- `title`: Article/case title
- `url`: Source URL
- `published`: Publication date (various formats)
- `body`: Main content text
- `source`: Data source identifier

### Module Organization

**main.py** - Primary entry point
- Single command interface for all operations
- Handles scraping, loading, and full pipeline execution

**src/utils/** - Shared utilities
- `http.py`: HTTP session management with proper User-Agent
- `keywords.py`: Basic fraud keyword matching for filtering during scraping

**src/detect/** - Fraud detection
- `fraud_detector.py`: Extended fraud detection with scoring

**src/database/** - Database operations
- `supabase_load.py`: Loads JSONL files into Supabase with fraud detection

**src/scripts/** - Helper scripts (legacy, prefer main.py)
- `run_scraper.py`: Run individual scrapers by name
- `run_all_scrapers.py`: Run all scrapers in sequence

### Fraud Detection System
Two-tier keyword matching system:

**Tier 1: Content Filtering** ([src/utils/keywords.py](src/utils/keywords.py))
- Used during scraping to filter relevant content
- Function: `is_fraud(text, min_hits=1)`
- Basic fraud terms: fraud, scam, phishing, identity theft

**Tier 2: Classification** ([src/detect/fraud_detector.py](src/detect/fraud_detector.py))
- Used during database loading for final classification
- Function: `detect_fraud_for_record(rec, min_hits=2)`
- Extended keyword list (16+ terms) including: business email compromise, ransomware, money mules, etc.
- Enriches records with: `is_fraud`, `fraud_hits`, `fraud_score`

### Database Loading Architecture
[src/database/supabase_load.py](src/database/supabase_load.py) handles:
- **File source mapping**: Maps JSONL files to source/feed metadata
- **Record normalization**: Converts varying scraper formats to unified schema
- **Date parsing**: Handles multiple date formats from different sources
- **Deduplication**: Keeps highest fraud_score for duplicate URLs
- **Batch upserts**: 500 records per batch, upserts on URL conflict
- **Fraud filtering**: Only loads records marked as fraud with valid title/URL

Target table: `fraud_articles` with fields:
- `source`, `feed`, `title`, `url`, `published_at`
- `body`, `summary`
- `is_fraud`, `fraud_hits`, `fraud_score`

### Legacy Code
The `archive/progress_report_1/` directory contains earlier scraper versions that have been superseded by the current organized structure.

## Output Data Format

JSONL files contain one JSON object per line:
```json
{
  "title": "FTC Takes Action Against...",
  "url": "https://www.ftc.gov/...",
  "published": "2024-11-02",
  "body": "Full article text...",
  "source": "FTC Press Releases"
}
```

After fraud detection enrichment:
```json
{
  ...
  "is_fraud": true,
  "fraud_hits": 5,
  "fraud_score": 5.0
}
```
