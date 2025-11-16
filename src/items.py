import scrapy

class PressReleaseItem(scrapy.Item):
    """FTC Press Release Item"""
    title = scrapy.Field()
    url = scrapy.Field()
    published_date = scrapy.Field()

    # Content
    full_text = scrapy.Field()
    summary = scrapy.Field()
    # Tags
    tags = scrapy.Field()
    # Metadata
    scraped_at = scrapy.Field()


class DataSpotlightItem(scrapy.Item):
    """FTC Data Spotlight Item"""
    title = scrapy.Field()
    url = scrapy.Field()
    published_date = scrapy.Field()

    # Content
    full_text = scrapy.Field()
    summary = scrapy.Field()

    # Tags
    tags = scrapy.Field()

    # Images
    images = scrapy.Field()
    image_urls = scrapy.Field()

    # Statistics and sources
    relevant_data = scrapy.Field()
    sources = scrapy.Field()

    # Metadata
    scraped_at = scrapy.Field()
