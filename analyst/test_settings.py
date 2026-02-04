"""
Test settings for running Django tests with a separate test database.
Uses a test collection named 'activities_test' that gets cleared after tests.

Usage:
    python manage.py test activities --settings=analyst.test_settings
"""
from analyst.settings import *

# Override database name for testing
# Django will automatically prefix with 'test_' but we explicitly set it here
DATABASES['default']['NAME'] = 'activities_test'

# Disable debugging during tests for better performance
DEBUG = False

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster test runs (optional - comment out if you need migrations)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()

# Reduce logging noise during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Disable email sending during tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable caching during tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use database sessions for testing (simpler than Redis)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
