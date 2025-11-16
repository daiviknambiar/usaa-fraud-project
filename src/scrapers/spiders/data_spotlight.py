"""
FTC Data Spotlight Spider

Scrapes data spotlight articles from https://www.ftc.gov/news-events/data-visualizations/data-spotlight
Scrapes all 2 pages (30 total articles)
"""
import scrapy
from datetime import datetime
from items import DataSpotlightItem
import re


class DataSpotlightSpider(scrapy.Spider):
    name = "data_spotlight"
    allowed_domains = ["ftc.gov"]
    start_urls = ["https://www.ftc.gov/news-events/data-visualizations/data-spotlight"]

    # Page limit - 2 pages with 30 total articles
    max_pages = 2
    pages_crawled = 0

    custom_settings = {
        'FEEDS': {
            'data/ftc_data_spotlight_scrapy.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
            },
        },
        'IMAGES_STORE': 'data/images',
        'ITEM_PIPELINES': {
            'scrapy.pipelines.images.ImagesPipeline': 1,
            'pipelines.SupabasePipeline': 300,
        },
    }

    # Try to exclude social media icons from image downloads
    social_media_patterns = [
        'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
        'youtube.com', 'pinterest.com', 'reddit.com', 'social',
        'share', 'tweet', 'fb.', 'addthis.com'
    ]

    def parse(self, response):
        """Parse the data spotlight listing page"""
        self.pages_crawled += 1
        self.logger.info(f"Parsing page {self.pages_crawled}: {response.url}")

        # Extract data spotlight articles
        articles = response.css('.views-row')

        if not articles:
            articles = response.css('article')

        self.logger.info(f"Processing {len(articles)} articles on page {self.pages_crawled}")

        for article in articles:
            # Extract the title link
            title_link = article.css('h2 a, h3 a, .title a, .field--name-title a')

            if not title_link:
                continue

            link = title_link.css('::attr(href)').get()
            if link and '/data-spotlight/' in link:
                article_url = response.urljoin(link)

                date_elem = article.css('time')
                date_text = date_elem.css('::attr(datetime)').get()
                if not date_text:
                    date_text = date_elem.css('::text').get()

                self.logger.info(f"Found article: {article_url} ({date_text})")

                yield response.follow(article_url, callback=self.parse_article,
                                     meta={'date_text': date_text})

        # Handle pagination within page limit
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
        """Parse individual data spotlight article"""
        self.logger.info(f"Parsing article: {response.url}")

        item = DataSpotlightItem()
        item['url'] = response.url
        item['scraped_at'] = datetime.now().isoformat()

        # Extract title
        title = response.css('h1::text, .page-title::text, article h1::text').get()
        item['title'] = title.strip() if title else None

        # Extract date
        date_text = response.meta.get('date_text') or response.css('time::attr(datetime), time::text, .date::text').get()
        item['published_date'] = self.parse_date(date_text)

        # Extract full text content
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

        # Extract summary (first paragraph or meta description)
        summary = response.css('meta[name="description"]::attr(content)').get()
        if not summary and full_text:
            summary = full_text[0] if full_text else None
        item['summary'] = summary

        # Extract tags
        tags = response.css('.field--name-field-tags a::text, .tags a::text, [class*="tag"] a::text').getall()
        item['tags'] = [tag.strip() for tag in tags if tag.strip()]

        # Extract images (excluding social media icons and PDFs)
        image_urls = []
        all_images = response.css('article img, .content img, .field--name-body img').css('::attr(src)').getall()

        for img_url in all_images:
            if self.is_social_media_image(img_url) or img_url.lower().endswith('.pdf'):
                continue

            # Make absolute URL
            abs_url = response.urljoin(img_url)
            image_urls.append(abs_url)

        item['image_urls'] = image_urls
        item['images'] = []  # Will be populated by ImagesPipeline

        # Extract sources and statistics
        sources_data = self.extract_sources_and_stats(response)
        item['relevant_data'] = sources_data.get('all_data', [])
        item['sources'] = sources_data.get('sources', [])

        yield item

    def is_social_media_image(self, url):
        """Check if image URL is for social media"""
        if not url:
            return False

        url_lower = url.lower()
        return any(pattern in url_lower for pattern in self.social_media_patterns)

    def extract_sources_and_stats(self, response):
        """Extract sources and statistics from the article"""
        sources_data = {
            'sources': [],
            'all_data': []
        }

        # Look for sources section 
        sources_selectors = [
            '.field--name-field-sources',
            '.sources',
            '[class*="source"]',
            'article ol, article ul',  
        ]

        for selector in sources_selectors:
            source_elements = response.css(selector)

            if source_elements:
                # Extract list items as individual sources
                list_items = source_elements.css('li')

                for idx, li in enumerate(list_items, 1):
                    # Get text content
                    text = ' '.join(li.css('::text').getall()).strip()

                    # Extract any links
                    links = li.css('a::attr(href)').getall()

                    if text:
                        source_entry = {
                            'index': idx,
                            'text': text,
                            'links': [response.urljoin(link) for link in links] if links else []
                        }

                        # Try to extract statistics from the text
                        stats = self.extract_statistics(text)
                        if stats:
                            source_entry['statistics'] = stats

                        sources_data['sources'].append(source_entry)
                        sources_data['all_data'].append(text)

                # If we found sources, break
                if sources_data['sources']:
                    break

        # Also look for any standalone statistics in the content
        stat_pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|percent|million|billion|thousand))?\b'
        all_text = ' '.join(response.css('article ::text, .content ::text').getall())

        # Find sentences with numbers that might be statistics
        sentences_with_stats = re.findall(r'[^.!?]*\d+[^.!?]*[.!?]', all_text)

        if sentences_with_stats and not sources_data['all_data']:
            sources_data['all_data'] = [s.strip() for s in sentences_with_stats[:10]]  # Limit to 10

        return sources_data

    def extract_statistics(self, text):
        """Extract numerical statistics from text"""
        stats = []

        # Pattern to match numbers with common statistical formats
        patterns = [
            r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|percent)\b',  # Percentages
            r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|thousand)\b',  # Large numbers
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|thousand)?\b',  # Dollar amounts
            r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b',  # Any number
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                stats.extend([' '.join(m) if isinstance(m, tuple) else m for m in matches])

        return list(set(stats))  # Remove duplicates

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
