# Set up the Twisted reactor BEFORE any imports that might use it
import os
os.environ['TWISTED_REACTOR'] = 'twisted.internet.selectreactor.SelectReactor'

# Then import modules
from . import translator
