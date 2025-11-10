"""
Utilities for Scrapy and Crochet integration.
"""

import os
import logging

logger = logging.getLogger(__name__)


def setup_twisted_reactor():
    """
    Ensure the correct Twisted reactor is set in the environment.
    This must be called BEFORE any Twisted imports or reactor installation.
    """
    # Use EPollReactor which is the default on Linux and most efficient
    reactor_class = 'twisted.internet.epollreactor.EPollReactor'
    os.environ['TWISTED_REACTOR'] = reactor_class
    logger.info(f"Set TWISTED_REACTOR to {reactor_class}")
    
    return reactor_class