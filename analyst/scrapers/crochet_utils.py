"""
Crochet utilities for running Scrapy spiders with Twisted in a Django/Celery environment.

This module provides a wrapper around Scrapy's CrawlerRunner using Crochet to allow
running Scrapy spiders in a Celery worker without interfering with the Twisted reactor.
"""

import logging
import os
from functools import wraps

# Ensure the correct Twisted reactor is set
from analyst.scrapers.utils import setup_twisted_reactor
setup_twisted_reactor()

# Now import Crochet and Scrapy modules
from crochet import setup, wait_for
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

# Configure crochet to initialize the reactor in a thread
setup()

logger = logging.getLogger(__name__)

# Load our custom settings
from analyst.scrapers import settings as spider_settings

# Get project settings and update with our custom settings
settings = get_project_settings()
settings.setmodule(spider_settings)

# Global CrawlerRunner instance to be used across all spiders
crawler_runner = CrawlerRunner(settings)


def run_spider(spider_cls, **kwargs):
    """
    Run a spider using Crochet and CrawlerRunner.
    
    This function is decorated with @wait_for which means it will wait
    for the deferred to fire and then return the result.
    
    Args:
        spider_cls: The Spider class to run
        **kwargs: Additional keyword arguments to pass to the spider
    
    Returns:
        The result from running the spider
    """
    @wait_for(timeout=480)  # 3 minutes timeout
    def _run_spider_with_crochet():
        return crawler_runner.crawl(spider_cls, **kwargs)
    
    try:
        logger.info(f"Starting spider: {spider_cls.name}")
        # Run the spider and wait for it to finish
        result = _run_spider_with_crochet()
        logger.info(f"Spider {spider_cls.name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error running spider {spider_cls.name}: {str(e)}")
        raise


def crochet_spider_task(func):
    """
    Decorator for Celery tasks that run Scrapy spiders.
    
    This wrapper ensures proper error handling and logging for spider tasks.
    
    Args:
        func: The task function to decorate
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"Starting spider task: {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"Spider task completed: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in spider task {func.__name__}: {str(e)}")
            raise
    
    return wrapper
