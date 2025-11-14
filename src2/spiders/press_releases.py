"""
FTC Press Releases Spider

Scrapes press releases from https://www.ftc.gov/news-events/news/press-releases
Scrapes the first 4 pages only, dating back to June 2025, to mimic data from the previous quarter.
"""
import scrapy
from datetime import datetime
from items import PressReleaseItem


class PressReleasesSpider(scrapy.Spider):
    name = "press_releases"
    allowed_domains = ["ftc.gov"]
    start_urls = ["https://www.ftc.gov/news-events/news/press-releases"]

    # Page limit
    max_pages = 4
    pages_crawled = 0

    custom_settings = {
        'FEEDS': {
            'data/ftc_press_releases_scrapy.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
            },
        },
    }

    def parse(self, response):
        """Parse the press releases listing page"""
        self.pages_crawled += 1
        self.logger.info(f"Parsing page {self.pages_crawled}: {response.url}")

        # Extract press releases
        press_releases = response.css('.views-row')

        if not press_releases:
            press_releases = response.css('article')

        self.logger.info(f"Processing {len(press_releases)} press releases on page {self.pages_crawled}")

        for pr in press_releases:
            # Extract the title link
            title_link = pr.css('h2 a, h3 a, .title a, .field--name-title a')

            if not title_link:
                continue

            link = title_link.css('::attr(href)').get()
            if link and link.startswith('/news-events/news/press-releases/'):
                # Make absolute URL
                article_url = response.urljoin(link)

                # Extract date from listing
                date_elem = pr.css('time')
                date_text = date_elem.css('::attr(datetime)').get()
                if not date_text:
                    date_text = date_elem.css('::text').get()

                self.logger.info(f"Found article: {article_url} ({date_text})")

                # Follow the link to get full article content
                yield response.follow(article_url, callback=self.parse_article,
                                     meta={'date_text': date_text})

        # Handle pagination in page limit
        if self.pages_crawled < self.max_pages:
            next_page = response.css('a[rel="next"]::attr(href), .pager__item--next a::attr(href)').get()
            if next_page:
                self.logger.info(f"Following next page: {next_page}")
                yield response.follow(next_page, callback=self.parse)
            else:
                self.logger.info("No next page found")
        else:
            self.logger.info(f"Reached page limit ({self.max_pages} pages), stopping pagination")

    def parse_article(self, response):
        """Parse individual press release article"""
        self.logger.info(f"Parsing article: {response.url}")

        item = PressReleaseItem()
        item['url'] = response.url
        item['scraped_at'] = datetime.now().isoformat()

        # Extract information
        title = response.css('h1::text, .page-title::text, article h1::text').get()
        item['title'] = title.strip() if title else None
        date_text = response.meta.get('date_text') or response.css('time::attr(datetime), time::text, .date::text').get()
        item['published_date'] = self.parse_date(date_text)
        content_selectors = [
            'article .content',
            '.field--name-body',
            '.node__content',
            'article',
            '.main-content',
        ]

        full_text = []
        for selector in content_selectors:
            paragraphs = response.css(f'{selector} p::text, {selector} p *::text').getall()
            if paragraphs:
                full_text = paragraphs
                break

        item['full_text'] = ' '.join(full_text).strip() if full_text else None

        # Extract summary (first paragraph or html description)
        summary = response.css('meta[name="description"]::attr(content)').get()
        if not summary and full_text:
            summary = full_text[0] if full_text else None
        item['summary'] = summary

        # Extract tags
        tags = response.css('.field--name-field-tags a::text, .tags a::text, [class*="tag"] a::text').getall()
        item['tags'] = [tag.strip() for tag in tags if tag.strip()]

        yield item

    def parse_date(self, date_text):
        """Parse date string into standardized format"""
        if not date_text:
            return None

        date_text = date_text.strip()

        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%SZ',  
            '%Y-%m-%dT%H:%M:%S',
            '%B %d, %Y',
            '%b %d, %Y',
            '%m/%d/%Y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_text, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # Try parsing ISO format with timezone
        try:
            if 'T' in date_text:
                dt = datetime.fromisoformat(date_text.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
        except:
            pass

        # If no format matches, return as-is
        return date_text
