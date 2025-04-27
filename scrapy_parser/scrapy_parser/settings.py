import os


BOT_NAME = "scrapy_parser"
SPIDER_MODULES = ["scrapy_parser.spiders"]
NEWSPIDER_MODULE = "scrapy_parser.spiders"

# Заголовки
DEFAULT_REQUEST_HEADERS = {
    'accept': '*/*',
    'accept-language': 'ru,ru-RU;q=0.9,en-US;q=0.8,en;q=0.7,th;q=0.6',
    'priority': 'u=1, i',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
}

# Настройка запросов
DOWNLOAD_DELAY = 0.3
CONCURRENT_REQUESTS = 10 # Ограничение на 10 одновременных запросов
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.3
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 5.0
AUTOTHROTTLE_HTTP_ERROR_CODES = [429, 503, 504]

# Прокси
PROXY_FILE_PATH = "proxy_http_ip.txt"
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