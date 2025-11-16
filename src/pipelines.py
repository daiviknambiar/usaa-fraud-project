
from itemadapter import ItemAdapter
import logging


class FtcScraperPipeline:
    """Main pipeline for processing scraped items"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.items_processed = 0

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # Checking if fields exist
        if not adapter.get('title'):
            raise DropItem(f"Missing title in {adapter.get('url')}")

        if not adapter.get('url'):
            raise DropItem("Missing URL")

        if adapter.get('title'):
            adapter['title'] = adapter['title'].strip()

        if adapter.get('full_text'):
            adapter['full_text'] = adapter['full_text'].strip()

        if adapter.get('summary'):
            adapter['summary'] = adapter['summary'].strip()

        # Log progress
        self.items_processed += 1
        if self.items_processed % 10 == 0:
            self.logger.info(f"Processed {self.items_processed} items")

        return item


class DropItem(Exception):
    """Exception to drop an item from the pipeline"""
    pass
