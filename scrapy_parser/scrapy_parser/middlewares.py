import logging
import os
from itertools import cycle

from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.http import Request, Response
from scrapy.spiders import Spider
from w3lib.http import basic_auth_header


class ProxyMiddleware:
    """Middleware для ротации HTTP-прокси из файла с авторизацией.

    Читает список прокси из файла, указанного в настройках, и циклически применяет их к запросам.
    Поддерживает авторизацию прокси через заголовок Proxy-Authorization.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, proxy_file_path: str, proxy_auth: dict):
        self.proxy_file_path = proxy_file_path
        self.proxy_auth = proxy_auth
        self.proxies: list[str] = []
        self.proxy_cycle = None
        self._load_proxies()

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        """Создание middleware из настроек Scrapy.
        """
        # Получаем настройки из settings.py
        proxy_file_path: str = crawler.settings.get('PROXY_FILE_PATH', cls._default_proxy_file_path())
        proxy_auth: dict[str, str] = crawler.settings.getdict('PROXY_AUTH', {})

        middleware = cls(proxy_file_path, proxy_auth)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def _load_proxies(self) -> None:
        """Загрузка списка прокси из файла.
        """
        if not os.path.exists(self.proxy_file_path):
            self.logger.error(f"Файл прокси не найден: {self.proxy_file_path}")
            return

        try:
            with open(self.proxy_file_path, 'r', encoding='utf-8') as proxy_file:
                self.proxies = list(map(str.strip, proxy_file.readlines())) # Убираем символ переноса строки
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла прокси {self.proxy_file_path}: {e}")
            return

        if not self.proxies:
            self.logger.warning(f"Файл прокси {self.proxy_file_path} пуст")
            return

        self.proxy_cycle = cycle(self.proxies)
        self.logger.info(f"Загружено {len(self.proxies)} прокси из {self.proxy_file_path}")

    def process_request(self, request: Request, spider: Spider) -> None:
        """Обработка запроса: установка прокси и авторизации.
        """
        if not self.proxy_cycle:
            self.logger.debug("Прокси не настроены, запрос выполняется без прокси")
            return None

        proxy = next(self.proxy_cycle)
        request.meta['proxy'] = f"http://{proxy}"

        # Установка авторизации, если указаны учетные данные
        if self.proxy_auth:
            username = self.proxy_auth.get('username', '')
            password = self.proxy_auth.get('password', '')
            request.headers['Proxy-Authorization'] = basic_auth_header(username, password)

        self.logger.debug(f"Используется прокси: {proxy} для {request.url}")
        return None

    def spider_opened(self, spider: Spider) -> None:
        """Обработка сигнала открытия паука.
        """
        self.logger.info(f"Паук открыт: {spider.name}")

    @staticmethod
    def _default_proxy_file_path() -> str:
        """Получение пути к файлу прокси по умолчанию.
        """
        return os.path.abspath(os.path.join(os.getcwd(), "proxy_http_ip.txt"))


class ProxyRetryMiddleware:
    """Middleware для повтора запросов с новым прокси при определенных HTTP-ошибках.

    Проверяет HTTP-коды ответа и, если код входит в список ошибок (например, 403, 429),
    заменяет текущий прокси на новый и повторяет запрос.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, retry_http_codes: list[int], max_retries: int):
        self.retry_http_codes = retry_http_codes # Список HTTP-кодов для повтора запроса.
        self.max_retries = max_retries # Максимальное количество повторов для одного запроса.

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> 'ProxyRetryMiddleware':
        """Создание middleware из настроек Scrapy.
        """
        retry_http_codes = crawler.settings.getlist('RETRY_HTTP_CODES', [403, 429])
        max_retries = crawler.settings.getint('RETRY_TIMES', 3)
        return cls(retry_http_codes, max_retries)

    def process_response(self, request: Request, response: Response, spider: Spider) -> Request | Response:
        """Обработка ответа: повтор запроса с новым прокси при ошибке.
        """
        if response.status in self.retry_http_codes:
            # Проверяем количество предыдущих повторов
            retries = request.meta.get('proxy_retry_count', 0)
            if retries >= self.max_retries:
                self.logger.error(
                    f"Достигнуто максимальное количество повторов ({self.max_retries}) "
                    f"для {request.url} с кодом {response.status}"
                )
                return response

            # Увеличиваем счетчик повторов
            retries += 1
            request.meta['proxy_retry_count'] = retries

            # Удаляем текущий прокси, чтобы ProxyMiddleware выбрал новый
            if 'proxy' in request.meta:
                old_proxy = request.meta['proxy']
                self.logger.warning(
                    f"Ошибка {response.status} для {request.url} с прокси {old_proxy}, "
                    f"попытка {retries}/{self.max_retries}"
                )
                del request.meta['proxy']
                request.headers.pop('Proxy-Authorization', None)  # Удаляем старую авторизацию

            # Повторяем запрос
            return request.replace(dont_filter=True)

        return response