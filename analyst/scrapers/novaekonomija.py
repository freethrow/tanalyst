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
import scrapy
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
            logger.info(f"Successfully saved article: {item.get('title_rs', 'Unknown')}")
            return item

        except DuplicateKeyError:
            logger.info(f"Duplicate article found: {item.get('title_rs', 'Unknown')}")
            raise DropItem(f"Duplicate article found: {item.get('title_rs', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error saving article to MongoDB: {str(e)}")
            raise


class NovaEkonomijaSpider(CrawlSpider):
    name = "novaekonomija"
    allowed_domains = ["novaekonomija.rs"]
    start_urls = [
        "https://novaekonomija.rs/vesti-iz-zemlje",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 10,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "COOKIES_ENABLED": False,
        "DOWNLOAD_TIMEOUT": 15,
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            __name__ + ".RandomUserAgentMiddleware": 400,
        },
        "ITEM_PIPELINES": {
            __name__ + ".MongoDBPipeline": 300,
        },
    }

    rules = [
        # Rule for article pages
        Rule(
            LinkExtractor(
                allow=r"/vesti-iz-zemlje/[a-z0-9-]+$",
                deny=r"/vesti-iz-zemlje/page/",  # Don't treat pagination as articles
            ),
            callback="parse_article",
            follow=False,
        ),
        # Rule for pagination - page 2 only
        Rule(
            LinkExtractor(
                allow=r"/vesti-iz-zemlje/page/2$",
            ),
            follow=True,
        ),
    ]

    def parse_start_url(self, response):
        """Override to manually extract article links and debug."""
        logger.info(f"🔍 Parsing start URL: {response.url}")

        # Debug: Find all links on the page
        all_links = response.css("a::attr(href)").getall()
        logger.info(f"📊 Found {len(all_links)} total links on page")

        # Find article links specifically
        article_links = response.css("article a::attr(href)").getall()
        logger.info(f"📰 Found {len(article_links)} article links")

        # Debug: Print first few article links
        for i, link in enumerate(article_links[:5]):
            logger.info(f"  Link {i + 1}: {link}")

        # Manually extract and follow article links
        for link in article_links:
            if link and "/vesti-iz-zemlje/" in link and "/page/" not in link:
                # Make absolute URL
                absolute_url = response.urljoin(link)
                logger.info(f"➡️  Following article: {absolute_url}")
                yield scrapy.Request(absolute_url, callback=self.parse_article)

        # Follow pagination to page 2
        page_2_link = response.css(
            "a[href*='/vesti-iz-zemlje/page/2']::attr(href)"
        ).get()
        if page_2_link:
            logger.info(f"📄 Found page 2 link: {page_2_link}")
            yield response.follow(page_2_link, callback=self.parse_start_url)
        else:
            # Try other pagination selectors
            page_2_link = response.xpath("//a[contains(@href, '/page/2')]/@href").get()
            if page_2_link:
                logger.info(f"📄 Found page 2 link (xpath): {page_2_link}")
                yield response.follow(page_2_link, callback=self.parse_start_url)

        # Don't return anything here - we're manually yielding requests above
        return []

    def parse_article(self, response):
        """Extract article data from the response."""
        try:
            logger.info(f"📄 Parsing article: {response.url}")

            # Extract title - try multiple selectors
            title = (
                response.css(".single-news-title::text").get()
                or response.css("h1.single-news-title::text").get()
                or response.css("h1::text").get()
                or response.xpath("//h1/text()").get()
            )

            if title:
                title = title.strip()
            else:
                logger.warning(f"⚠️  No title found for {response.url}")
                # Debug: Show what h1 content exists
                h1_elements = response.css("h1").getall()
                logger.debug(f"H1 elements found: {h1_elements[:200]}")
                return None

            # Extract date and time from p.time-date
            date_spans = response.css("p.time-date span::text").getall()

            if len(date_spans) >= 2:
                try:
                    date_str = date_spans[0].strip()
                    time_str = date_spans[1].strip()

                    # Remove trailing dot from date
                    date_str = date_str.rstrip(".")

                    # Split date parts and construct in correct order
                    day, month, year = date_str.split(".")
                    formatted_date = f"{year}-{month}-{day}"

                    # Combine date and time
                    date_time_str = f"{formatted_date} {time_str}"
                    naive_date = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")

                    # Add timezone (Serbian time)
                    serbian_tz = pytz.timezone("Europe/Belgrade")
                    local_date = serbian_tz.localize(naive_date)

                    # Convert to UTC
                    date = local_date.astimezone(pytz.UTC)
                    logger.info(
                        f"📅 Successfully parsed date: {date_time_str} to {date}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error parsing date '{date_str} {time_str}': {e}")
                    date = None
            else:
                logger.warning(f"⚠️  No date found for {response.url}")
                date = None

            # Extract content from .single-news while excluding specific divs we don't want
            main_content_selector = ".single-news"
            exclude_selectors = [
                ".single-news-footnote",
                ".single-news-tags", 
                ".comments-section"
            ]
            
            # Get all text from main content area
            content_parts = response.css(f"{main_content_selector} *::text").getall()
            
            # If nothing found, try article tag
            if not content_parts:
                content_parts = response.css("article *::text").getall()

            # If still nothing, try more general
            if not content_parts:
                content_parts = response.xpath("//article//p//text()").getall()

            # Clean content parts
            cleaned_parts = []
            for part in content_parts:
                part = part.strip()
                # Skip empty parts or non-breaking spaces
                if not part or part == "\xa0" or part == "&nbsp;":
                    continue
                # Skip parts that appear to be from excluded divs
                skip = False
                for selector in exclude_selectors:
                    if response.css(f"{selector} *::text").getall() and part in response.css(f"{selector} *::text").getall():
                        skip = True
                        break
                if not skip:
                    cleaned_parts.append(part)
            
            # Join the cleaned content
            content = " ".join(cleaned_parts)

            if not content:
                logger.warning(f"⚠️  No content found for {response.url}")
                content = "No content extracted"

            # Create item
            item = {
                "title_rs": title,
                "article_date": date,
                "content_rs": content,
                "url": response.url,
                "source": "novaekonomija.rs",
                "status": "PENDING",
            }

            logger.info(f"Successfully parsed article: {title}")
            return item

        except Exception as e:
            logger.error(f"❌ Error parsing article {response.url}: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
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
        
        logger.info("Starting Nova Ekonomija spider...")
        return run_spider(NovaEkonomijaSpider)

    except Exception as e:
        logger.error(f"Error running spider: {str(e)}")
        raise


if __name__ == "__main__":
    main()