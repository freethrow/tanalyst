# biznisrs.py

from datetime import datetime
import os
import logging
import random

import pymongo
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerRunner
from scrapy.exceptions import DropItem
from scrapy import signals
import pytz

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class MongoDBPipeline:
    """Pipeline for storing scraped items in MongoDB."""

    def __init__(self):
        self.mongo_uri = os.getenv("MONGODB_URI")
        self.db_name = os.getenv("MONGO_DB")
        self.collection_name = os.getenv("MONGO_COLLECTION")
        self.client = None
        self.db = None
        self.collection = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider):
        """Initialize MongoDB connection when spider opens."""
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                minPoolSize=5,
                retryWrites=True,
                retryReads=True,
            )
            # Test connection
            self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB")

            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]

            # Create index on URL
            self.collection.create_index([("url", pymongo.ASCENDING)], unique=True)

        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {str(e)}")
            raise

    def close_spider(self, spider):
        """Clean up MongoDB connection when spider closes."""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")

    def process_item(self, item, spider):
        """Process and store items in MongoDB."""
        try:
            # Add timestamp
            item["scraped_at"] = datetime.utcnow()

            # Check if article with this URL already exists
            if self.collection.find_one({"url": item.get("url")}):
                logger.info(f"Article already exists: {item.get('url')}")
                return item  # Skip saving but still return item for other pipelines

            # Insert into MongoDB
            self.collection.insert_one(dict(item))
            logger.info(f"Successfully saved article: {item.get('title_rs', item.get('title_en', 'Unknown'))}")
            return item

        except DuplicateKeyError:
            logger.info(f"Duplicate article found: {item.get('title_rs', item.get('title_en', 'Unknown'))}")
            raise DropItem(f"Duplicate article found: {item.get('title_rs', item.get('title_en', 'Unknown'))}")

        except Exception as e:
            logger.error(f"Error saving article to MongoDB: {str(e)}")
            raise


class BiznisRsSpider(CrawlSpider):
    name = "biznisrsspider"
    allowed_domains = ["biznis.rs"]
    start_urls = [
        "https://biznis.rs/vesti/srbija/",
        "https://biznis.rs/vesti/srbija/page/2/",
        "https://biznis.rs/vesti/srbija/page/3/",
        "https://biznis.rs/vesti/srbija/page/4/",
        "https://biznis.rs/vesti/srbija/page/5/",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 20,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "COOKIES_ENABLED": False,
        "DOWNLOAD_TIMEOUT": 180,  # 3 minutes timeout
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            __name__ + ".RandomUserAgentMiddleware": 400,
        },
        "ITEM_PIPELINES": {
            __name__ + ".MongoDBPipeline": 300,
        },
    }

    rules = [
        # Rule for article pages - extract links from div.title > h2
        Rule(
            LinkExtractor(
                allow=r"/vesti/.*",
                restrict_xpaths="//div[@class='title']//h2//a",
            ),
            callback="parse_article",
            follow=False,
        ),
    ]

    def parse_article(self, response):
        """Extract article data from the response."""
        try:
            # Extract title from h1
            title = response.css("h1::text").get()
            if title:
                title = title.strip()

            # Extract intro text if available
            intro = response.css(".intro::text").get()
            if intro:
                intro = intro.strip()

            # Extract content from div.post[itemprop="articleBody"]
            content_blocks = []
            content_div = response.css('div.post[itemprop="articleBody"]')

            if content_div:
                # Get all text nodes from paragraphs and other elements
                text_parts = content_div.xpath(".//text()[normalize-space()]").getall()
                content_blocks.extend(text_parts)

            # Clean and join content
            content_parts = [part.strip() for part in content_blocks if part.strip()]
            content = " ".join(content_parts)

            # If we have intro, prepend it to content
            if intro and content:
                content = f"{intro} {content}"
            elif intro and not content:
                content = intro

            # Try to extract date - look for common date patterns
            date = None
            try:
                # Look for date in meta tags or structured data
                date_meta = response.css(
                    'meta[property="article:published_time"]::attr(content)'
                ).get()
                if date_meta:
                    date = datetime.fromisoformat(date_meta.replace("Z", "+00:00"))
                else:
                    # Look for date in text content - this might need adjustment based on actual site structure
                    date_text = response.css(
                        ".date, .published, .post-date::text"
                    ).get()
                    if date_text:
                        # Try to parse Serbian date format
                        date_text = date_text.strip()
                        # Add date parsing logic here if needed
                        logger.info(f"Found date text: {date_text}")
            except Exception as e:
                logger.warning(f"Could not parse date for {response.url}: {e}")
                date = None

            # Create item
            item = {
                "title_rs": title,
                "article_date": date,
                "content_rs": content,
                "url": response.url,
                "source": "biznis.rs",
                "status": "PENDING",
            }

            logger.info(f"Successfully parsed article: {title}")
            return item

        except Exception as e:
            logger.error(f"Error parsing article {response.url}: {str(e)}")
            return None

    def closed(self, reason):
        """Log when spider is closed."""
        logger.info(f"Spider closed: {reason}")


class RandomUserAgentMiddleware:
    """Middleware to rotate User-Agents for each request."""

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self.user_agents = self.user_agents

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_request(self, request, spider):
        user_agent = random.choice(self.user_agents)
        request.headers["User-Agent"] = user_agent
        return None

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


def main():
    """Run the spider."""
    try:
        # Verify environment variables
        required_vars = ["MONGODB_URI", "MONGO_DB", "MONGO_COLLECTION"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        # Import run_spider from crochet_utils to avoid circular imports
        from analyst.scrapers.crochet_utils import run_spider
        
        logger.info("Starting Biznis.rs spider...")
        return run_spider(BiznisRsSpider)

    except Exception as e:
        logger.error(f"Error running spider: {str(e)}")
        raise


if __name__ == "__main__":
    main()
