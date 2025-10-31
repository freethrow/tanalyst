"""
Crochet setup for Django integration with Twisted/Scrapy.

This module initializes Crochet when the Django app starts, allowing
Scrapy spiders to run within a Celery worker without blocking the
Twisted reactor.
"""

import logging
import os
from django.apps import AppConfig

# Configure logging
logger = logging.getLogger(__name__)

# Force Twisted to use SelectReactor (MUST BE DONE BEFORE ANY TWISTED IMPORT)
os.environ['TWISTED_REACTOR'] = 'twisted.internet.selectreactor.SelectReactor'


class CrochetAppConfig(AppConfig):
    """Django AppConfig that initializes Crochet on startup."""
    
    name = 'analyst'
    verbose_name = 'Analyst'
    
    def ready(self):
        """
        Called when the Django app is ready.
        This initializes Crochet for the entire application.
        """
        try:
            # Import and setup crochet
            from crochet import setup
            setup()
            
            # Verify the reactor is correctly configured
            from twisted.internet import reactor
            logger.info(f"Crochet setup complete - Using Twisted reactor: {reactor.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error setting up Crochet: {str(e)}")
            # Don't re-raise the exception to allow the app to start even if Crochet setup fails
            # This is better than crashing the entire application
