# Set up the Twisted reactor BEFORE any imports that might use it
from .utils import setup_twisted_reactor
setup_twisted_reactor()

# Import all scrapers for easy access
from . import ekapija
from . import biznisrs
from . import novaekonomija
