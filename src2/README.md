# FTC Press Releases Scrapy Spider

A Scrapy-based web scraper for extracting FTC press releases from https://www.ftc.gov/news-events/news/press-releases

## Features

- ✅ Scrapes press releases from the first 4 pages (~80 articles)
- ✅ Extracts full article text
- ✅ Extracts publication dates
- ✅ Captures article tags/categories
- ✅ Handles pagination automatically (up to 4 pages)
- ✅ Respects robots.txt and implements polite crawling delays
- ✅ Outputs to structured JSON format

## Project Structure

```
src2/
├── data/                              # Output directory
│   └── ftc_press_releases_scrapy.json # Scraped data
├── spiders/                           # Spider modules
│   ├── __init__.py
│   └── press_releases.py              # Main spider
├── items.py                           # Data structure definitions
├── pipelines.py                       # Data processing pipelines
├── settings.py                        # Scrapy settings
├── scrapy.cfg                         # Scrapy configuration
├── run_spider.sh                      # Convenient run script
└── README.md                          # This file
```

## Installation

The spider requires Scrapy. Install from the project root:

```bash
pip install -r requirements.txt
```

Or install Scrapy directly:

```bash
pip install Scrapy==2.11.0
```

## Usage

### Using the run script (recommended)

```bash
cd src2
./run_spider.sh
```

### Using scrapy directly

```bash
cd src2
python3 -m scrapy crawl press_releases
```

### Enable debug logging

```bash
./run_spider.sh --debug
```

## Output

### JSON Data

The spider outputs data to:
```
src2/data/ftc_press_releases_scrapy.json
```

Each article contains:
- `url`: Article URL
- `title`: Article title
- `published_date`: Publication date (YYYY-MM-DD format)
- `full_text`: Complete article text
- `summary`: Article summary (from meta description or first paragraph)
- `tags`: List of article tags/categories
- `scraped_at`: Timestamp when the article was scraped

### Example Output

```json
{
  "url": "https://www.ftc.gov/news-events/news/press-releases/2025/09/...",
  "title": "Ed Tech Provider Chegg to Pay $7.5 Million...",
  "published_date": "2025-09-15",
  "full_text": "Chegg Inc. will be required to pay...",
  "summary": "Chegg Inc.",
  "tags": ["Consumer Protection", "Education", "Technology"],
  "scraped_at": "2025-11-13T22:19:27.722899"
}
```

## Configuration

### Page Limit

To change the number of pages scraped, edit [spiders/press_releases.py](spiders/press_releases.py):

```python
max_pages = 4  # Change this number
```

### Crawl Settings

Key settings in [settings.py](settings.py):
- `DOWNLOAD_DELAY`: Delay between requests (default: 1 second)
- `CONCURRENT_REQUESTS`: Number of concurrent requests (default: 8)
- `USER_AGENT`: Browser identification string
- `ROBOTSTXT_OBEY`: Whether to obey robots.txt (default: True)

## Results

Based on the most recent run:
- **Total articles scraped**: 80
- **Pages crawled**: 4
- **Date range**: June 25, 2025 to October 17, 2025
- **Execution time**: ~1.7 minutes
- **Success rate**: 100%

## Troubleshooting

### 403 Forbidden Errors

If you get 403 errors:
1. Increase the `DOWNLOAD_DELAY` setting in [settings.py](settings.py)
2. Reduce `CONCURRENT_REQUESTS`
3. Check if your IP is being rate-limited

### Missing Data

If some fields are empty:
1. Check if the FTC website structure changed
2. Look at the spider logs for warnings
3. The HTML selectors may need updating in [spiders/press_releases.py](spiders/press_releases.py)

### Import Errors

If you get import errors, make sure you're running from the `src2` directory:
```bash
cd src2
python3 -m scrapy crawl press_releases
```

## Notes

- The spider respects robots.txt and implements polite crawling delays
- Configured to scrape the first 4 pages (approximately 80 articles)
- Articles from June 2025 to October 2025 are included
- No images are downloaded (text content only)
