"""
Crochet utilities for running async code in a Celery worker.

This module provides utilities for running asyncio-based code with Crochet
to ensure proper Twisted reactor management.
"""

import logging
import os
from functools import wraps

# Ensure the correct Twisted reactor is set
os.environ['TWISTED_REACTOR'] = 'twisted.internet.selectreactor.SelectReactor'

# Import crochet after setting the reactor environment variable
from crochet import setup, wait_for

# Initialize crochet
setup()

logger = logging.getLogger(__name__)


def crochet_async_task(timeout=480):
    """
    Decorator for running asyncio functions safely in a Celery worker using Crochet.
    
    Args:
        timeout: Maximum time to wait for async operation in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Define a Crochet-wrapped version of the function
                @wait_for(timeout=timeout)
                def run_with_crochet():
                    return func(*args, **kwargs)
                
                logger.info(f"Running async task with Crochet: {func.__name__}")
                result = run_with_crochet()
                logger.info(f"Async task completed: {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Error in async task {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator
