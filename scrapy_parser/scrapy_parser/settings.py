import os


BOT_NAME = "scrapy_parser"
SPIDER_MODULES = ["scrapy_parser.spiders"]
NEWSPIDER_MODULE = "scrapy_parser.spiders"

# Настройка запросов
DOWNLOAD_DELAY = 0.3
CONCURRENT_REQUESTS = 10 # Ограничение на 10 одновременных запросов
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Прокси
PROXY_FILE_PATH = os.path.abspath(os.path.join(os.getcwd(), "proxy_http_ip.txt"))
PROXY_AUTH = {
    'username': 'irusp1050411',
    'password': 'SGvSzxMcJb',
}

# Middleware
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware": None,
    "scrapy_parser.middlewares.ProxyMiddleware": 350,
    "scrapy_parser.middlewares.ProxyRetryMiddleware": 400,
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

# Повторные попытки при ошибках
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [403, 429, 500, 502, 503, 504]

# Экспорт в JSON
FEEDS = {
    'result.json': {
        'format': 'json',
        'encoding': 'utf-8',
        'indent': 4,
        'overwrite': True,
    }
}

# Дополнительные настройки
COOKIES_ENABLED = False # Отключение куки

# Логирование
LOG_LEVEL = 'INFO'
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"