import os
import scrapy
import time
import json
from urllib.parse import urlencode
from scrapy.http import Response
from typing import Any
from ..items import ScrapyItem


class AlkotekaSpider(scrapy.Spider):
    name = "alkoteka"
    allowed_domains = ["alcoteka.com"]

    # UUID городов в параметрах API
    CITIES_ID: dict = {
        "Москва": "396df2b5-7b2b-11eb-80cd-00155d039009",
        "Краснодар": "4a70f9e0-46ae-11e7-83ff-00155d026416",
        "Ростов-на-Дону": "878a9eb4-46b2-11e7-83ff-00155d026416",
        "Сочи": "985b3eea-46b4-11e7-83ff-00155d026416"
    }

    def __init__(self, city="Краснодар", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.input_file_path = os.path.abspath(os.path.join(os.getcwd(), "input_urls.txt"))
        try:
            with open(self.input_file_path, 'r', encoding='utf-8') as inp_file:
                self.INPUT_URLS = [line.strip() for line in inp_file if line.strip()]
        except FileNotFoundError:
            self.logger.error(f"Файл {self.input_file_path} не найден")
            self.INPUT_URLS = []
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла {self.input_file_path}: {e}")
            self.INPUT_URLS = []

    def start_requests(self):
        """Парсинг категорий из файла"""
        if not self.INPUT_URLS:
            self.logger.error("Нет категорий для обработки. Проверьте input_urls.txt")
            return

        # UUID требуемого города
        city_id = self.CITIES_ID.get(self.city, self.CITIES_ID["Краснодар"])

        for category_url in self.INPUT_URLS:
            # Получаем название категории из ссылки
            category_name = category_url.split('/')[-1]

            params: dict[str, str] = {
                'city_uuid': city_id,
                'page': '1',
                'per_page': '10000',
                'root_category_slug': category_name
            }

            cat_url: str = f"https://alkoteka.com/web-api/v1/product?{urlencode(params)}"
            self.logger.info(f"Создаю запрос для категории {category_name}: {cat_url}")

            yield scrapy.Request(
                url=cat_url,
                callback=self.parse_category,
                meta={
                    'category_name': category_name,
                    'city_id': city_id
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                dont_filter=True
            )

    def parse_category(self, response: Response):
        """Парсинг списка товаров в категории."""
        city_id: str = response.meta['city_id']

        try:
            # Преобразуем ответ к json
            json_resp: dict[str, Any] = json.loads(response.text)

            total_goods: int = len(json_resp.get('results', [])) # Общее количество товаров в категории
            if not total_goods:
                self.logger.info(f"Товаров в данной категории нет: {response.url}")
                return

            category_name: str = json_resp['results'][0].get('category', {}).get('parent', {}).get('name', {})
            self.logger.info(f"Количество товаров в категории {category_name}: {total_goods}")

            # Получаем список "slug" товаров
            slugs: list[str] = list(map(lambda x: x.get('slug', ''), json_resp['results']))

            for slug in slugs:
                item_url: str = f"https://alkoteka.com/web-api/v1/product/{slug}?{urlencode({"city_uuid": city_id})}"
                self.logger.debug(f"URL: {item_url}")

                yield scrapy.Request(
                    url=item_url,
                    callback=self.parse_item,
                    meta={
                        "timestamp": int(time.time()),
                        "item_slug": slug
                    },
                    headers={
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
                )
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка декодирования JSON")
        except Exception as exx:
            self.logger.error(f"Ошибка в parse_category: {str(exx)}")


    def parse_item(self, response: Response):
        """Парсинг информации о товаре."""
        self.logger.info(f"Обрабатываю товар: {response.url}, статус: {response.status}")
        resp_timestamp: int = response.meta['timestamp']
        slug: str = response.meta["item_slug"]

        try:
            # Преобразуем ответ к json
            item_json: dict[str, Any] = json.loads(response.text)
            item: dict[str, Any] = item_json.get('results', {})
            if not item:
                self.logger.info(f"Информации о товаре нет")
                return

            # Получаем "объем" из фильтров товара для названия
            volume: str = ""
            for filter_label in item.get('filter_labels', []):
                filter_label: dict[str, Any]
                if filter_label.get('filter') == "obem":
                    volume: str = filter_label.get('title')
                    break

            # Получаем характеристики товара
            brand: str = ""
            all_chars: dict[str, str] = {}
            for char in item.get('description_blocks', []):
                char: dict[str, Any]

                # Получаем бренд товара
                if char.get('code') == "brend":
                    brand: str = char['values'][0].get('name', '')

                # Сохраняем характеристики в зависимости от вида
                match char.get('type'):
                    case "range":
                        all_chars[char['title']] = f"{char.get('max', '')}{char.get('unit', '')}"
                    case "select":
                        all_chars[char['title']] = char['values'][0].get('name', '')
                    case "flag":
                        all_chars[char['title']] = char['placeholder']

            # Создание объекта Item
            res_item = ScrapyItem()
            res_item['timestamp'] = resp_timestamp  # Дата и время сбора товара в формате timestamp
            res_item['RPC'] = item.get('vendor_code') # Артикул товара
            res_item['url'] = f"https://alkoteka.com/product/{item['category']['slug']}/{slug}"  # Ссылка на товар
            res_item['title'] = f"{item.get('name')} {volume}" if volume else f"{item.get('name')}"  # Название товара
            res_item['marketing_tags'] = [
                fl.get('title', '') for fl in item.get('filter_labels', []) # Список маркетинговых тэгов
            ]
            res_item['brand'] = brand # Бренд товара
            res_item['section']: [
                item['category']['parent'].get('name', ''), item['category'].get('name', '')
            ]  # Иерархия разделов
            res_item['price_data'] = {
                "current": float(item['price']) if item.get('price') else float(item.get('prev_price', 0)), # Цена со скидкой
                "original": float(item.get('prev_price', 0)),  # Оригинальная цена
                "sale_tag": f"Скидка {100 - round(100 * (item.get('price', 0) / item.get('prev_price', 0)))}%" # Процент скидки
            }
            res_item['stock'] = {
                "in_stock": item.get('available', False),  # Товар в наличии
                "count": item.get('quantity_total', 0)  # Количество оставшегося товара
            }
            res_item['assets'] = {
                "main_image": item.get('image_url', ''),  # Ссылка на основное изображение товара
                "set_images": [],
                "view360": [],
                "video": []
            }
            res_item['metadata'] = {
                "__description": "".join([
                    title.get('content', '').replace('<br>\n', '. ')
                    for title in item.get('text_blocks', []) if title.get('title', '') == 'Описание'
                ])  # Описание товара
            }
            res_item['variants'] = 1

            # Добавляем в результат характеристики товара
            res_item['metadata'].update(all_chars)

            yield res_item

        except json.JSONDecodeError:
            self.logger.error(f"Ошибка декодирования JSON")
        except Exception as e:
            self.logger.error(f"Ошибка в parse_item: {str(e)}")
