# Scrapy settings

# Configure Twisted reactor to use the SelectReactor (compatible with Crochet)
TWISTED_REACTOR = "twisted.internet.selectreactor.SelectReactor"

# Common settings for all spiders
BOT_NAME = 'analyst'

# Default User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Log level
LOG_LEVEL = "INFO"

# HTTP Cache settings
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [503, 504, 505, 500, 400, 401, 402, 403, 404]
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Default download settings
DOWNLOAD_TIMEOUT = 20
RANDOMIZE_DOWNLOAD_DELAY = True

# Extension settings
EXTENSIONS = {
   'scrapy.extensions.telnet.TelnetConsole': None,
}
