"""
Integration test for Crochet with Scrapy and Celery.

This script verifies that Crochet is set up correctly by running a simple
test that uses both the Scrapy spider and the translation functionality.

Run this directly to test without starting the full Celery worker.
"""

import os
import sys
import logging
from time import sleep

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set the Twisted reactor
os.environ['TWISTED_REACTOR'] = 'twisted.internet.selectreactor.SelectReactor'

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialize Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyst.settings")
import django
django.setup()

# Import our modules after Django is set up
from analyst.scrapers.crochet_utils import run_spider, crochet_spider_task
from analyst.agents.crochet_utils import crochet_async_task
from analyst.scrapers.ekapija import EkapijaSpider

# Test function for the translation task
async def test_async_translation():
    """Simulate an async translation task."""
    logger.info("Starting test async translation...")
    # Simulate work
    sleep(2)
    logger.info("Async translation completed!")
    return {"success": True, "message": "Translation completed"}

def test_translations():
    """Test running an async function with Crochet."""
    from analyst.agents.crochet_utils import crochet_async_task
    
    @crochet_async_task(timeout=30)
    def run_async_test():
        return test_async_translation()
    
    logger.info("Starting translation test...")
    result = run_async_test()
    logger.info(f"Translation test result: {result}")

def test_scrapers():
    """Test running a Scrapy spider with Crochet."""
    @crochet_spider_task
    def run_test_spider():
        logger.info("Starting scraper test...")
        # We'll initialize the spider without actually running it to avoid making real web requests
        return run_spider(EkapijaSpider, start_requests=False)
    
    result = run_test_spider()
    logger.info(f"Scraper test completed: {result}")

if __name__ == "__main__":
    logger.info("Starting integration test...")
    
    # Test translations first
    try:
        test_translations()
        logger.info("✅ Translation test passed")
    except Exception as e:
        logger.error(f"❌ Translation test failed: {str(e)}")
    
    # Test scrapers second
    try:
        test_scrapers()
        logger.info("✅ Scraper test passed")
    except Exception as e:
        logger.error(f"❌ Scraper test failed: {str(e)}")
    
    logger.info("Integration test completed")
