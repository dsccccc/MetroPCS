import argparse
import json
import time
from html import unescape

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup


class MetroPCS:
    def __init__(self):
        self.BASE_URL = 'https://www.metrobyt-mobile.com'
        self.APPLE_URL = 'https://www.metrobyt-mobile.com/cell-phones/brand/apple'

        self.urls = []
        self.products = {}

        self.output_dir: str = ''
        self.file_name: str = ''
        self.modes = None
        self.proxy: str = ''
        self.table: bool = True
        self.markdown: str = ''

        self.options = self._build_options()
        self._driver = self._new_driver()

    @staticmethod
    def _build_options() -> Options:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,2000")
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        )
        options.add_argument(f"user-agent={user_agent}")
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        # capture XHR responses (pricing / availability API) via CDP performance logs
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        return options

    def _new_driver(self) -> webdriver.Chrome:
        driver = webdriver.Chrome(self.options)
        driver.set_page_load_timeout(60)
        return driver

    def arg_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--output_dir', type=str, default='./metro/data/', help='Directory of output files.')
        parser.add_argument('--file_name', type=str, default='metro.md', help='Name of output markdown file.')
        parser.add_argument('--modes', type=str, default='["iPhone"]', help='Keywords to search for items.')
        parser.add_argument('--proxy', type=str, default='', help='Whether connect through proxy.')
        parser.add_argument('--table', action='store_true', help='Whether output Markdown tables.')
        args = parser.parse_args()
        self.output_dir = args.output_dir
        self.file_name = self.output_dir + args.file_name
        self.modes = eval(args.modes)
        self.proxy = args.proxy
        self.table = args.table
        if len(self.proxy) > 0:
            self.options.add_argument(f'--proxy-server=http://{self.proxy}')
            self._driver.close()
            self._driver = self._new_driver()

    def _get_families(self):
        """Load the brand listing page and extract product families from the
        server-rendered product cards."""
        # noinspection PyBroadException
        try:
            self._driver.get(self.APPLE_URL)
            WebDriverWait(self._driver, 30).until(
                lambda d: d.find_elements('css selector', 'li[data-upf-product-grid-item]'))
            soup = BeautifulSoup(self._driver.page_source, from_encoding='utf-8', features='html.parser')
        except Exception:
            self._driver.quit()
            time.sleep(5)
            self._driver = self._new_driver()
            return None
        families = []
        for card in soup.select('li[data-upf-product-grid-item]'):
            brand = self._visible_text(card, '.upf-productCard__title--brand')
            model = self._visible_text(card, '.upf-productCard__title--model')
            link = card.select_one('a.upf-productCard__content-link[href]')
            if not (brand and model and link):
                continue
            # the listing page renders the full catalog; keep the brand this repo tracks
            if brand != 'Apple':
                continue
            families.append({
                'name': f'{brand} {model}',
                'sku': card.get('data-upf-plp-card-sku', ''),
                'family_code': card.get('data-upf-plp-card-family-code', ''),
                'url': link['href'],
                'esim': 'eSIM' in (card.get('data-upf-plp-card-filter') or ''),
            })
        return families

    @staticmethod
    def _visible_text(card, selector: str) -> str:
        """First non-empty match that is not inside an unrendered <template> block."""
        for el in card.select(selector):
            if el.find_parent('template') is None and el.get_text(strip=True):
                return el.get_text(strip=True)
        return ''

    def _get_family_details(self, family):
        """Navigate to a product detail page, capture the product-promo-pricing
        API response (price/promos/availability/shipping per SKU) and read the
        variant -> (color, memory) mapping from the page."""
        url = family['url']
        if url.startswith('/'):
            url = self.BASE_URL + url
        self._driver.get(url)
        api_json = None
        deadline = time.time() + 30
        while time.time() < deadline:
            for entry in self._driver.get_log('performance'):
                message = json.loads(entry['message'])['message']
                if message.get('method') != 'Network.responseReceived':
                    continue
                if 'product-promo-pricing' not in message['params']['response']['url']:
                    continue
                body = self._driver.execute_cdp_cmd(
                    'Network.getResponseBody', {'requestId': message['params']['requestId']})
                api_json = json.loads(body.get('body', '{}'))
                break
            if api_json is not None:
                break
            time.sleep(0.5)
        variants = {}
        # noinspection PyBroadException
        try:
            raw = self._driver.execute_script(
                "const el = document.querySelector('.upf-skuSelector');"
                "return el ? el.getAttribute('data-upf-variants') : null;")
            if raw:
                for variant in json.loads(unescape(raw)):
                    variants[variant['sku']] = variant
        except Exception:
            pass
        return api_json, variants

    def getter(self):
        families = self._get_families()
        if families is None:
            return None
        rows = []
        for family in families:
            if type(self.modes) is list:
                for mode in self.modes:
                    if mode in family['name']:
                        break
                else:
                    continue
            elif type(self.modes) is str:
                if self.modes not in family['name']:
                    continue
            else:
                print('Invalid keywords!')
            # noinspection PyBroadException
            try:
                api_json, variants = self._get_family_details(family)
            except Exception:
                print(f"Failed to load {family['name']}, skipped.")
                time.sleep(2)
                continue
            if not api_json:
                print(f"No pricing data for {family['name']}, skipped.")
                continue
            for product in api_json.get('products', []):
                for sku in product.get('skus', []):
                    variant = variants.get(sku.get('skuCode'), {})
                    availability = sku.get('availability') or {}
                    price = (sku.get('frpPrice') or {}).get('salePrice')
                    if price is None:
                        continue
                    promotions = (sku.get('availableCartPromotions') or []) + \
                                 (sku.get('applicablePromotions') or [])
                    deal = max([promo['discountValue']['amount']
                                for promo in promotions if promo.get('discountValue')] or [0])
                    rows.append({
                        'name': family['name'],
                        'color': variant.get('color', ''),
                        'memory': variant.get('memory', ''),
                        'esim': 'eSIM' in (sku.get('defaultSimType') or '') or family['esim'],
                        'price': price - deal,
                        'status': availability.get('availabilityStatus', ''),
                        'shipping0': availability.get('estimatedShippingFromDateTime') or '',
                        'shipping1': availability.get('estimatedShippingToDateTime') or '',
                    })
            time.sleep(1)
        return rows

    def parser(self, rows):
        if not rows:
            print('No products found!')
            return
        len_name = max(len(row['name']) for row in rows)
        print(f'MetroPCS\t{time.strftime("%m/%d/%Y", time.localtime())}{" " * max(len_name - 16, 0)}\t'
              f'{"color":16s}\tmemory\teSIM\tprice\t{"status":13s}\t{"Shipping from":10s}\t{"to":10s}')
        self.markdown += (f'|MetroPCS {time.strftime("%m/%d/%Y", time.localtime())}|color|memory|eSIM|price|status'
                          f'|shipping from|shipping to|\n')
        self.markdown += '|:--:' * 8 + '|\n'
        for row in rows:
            print(f"{row['name']:{len_name}s}\t{row['color']:16s}\t{row['memory']}\t{row['esim']}\t"
                  f"{row['price']:.2f}\t{row['status']:13s}\t{row['shipping0']}\t{row['shipping1']}")
            self.markdown += (f"|{row['name']}|{row['color']}|{row['memory']}|{row['esim']}|{row['price']:.2f}"
                              f"|{row['status']}|{row['shipping0']}|{row['shipping1']}|\n")

    def writer(self):
        with open(self.file_name, 'w+', encoding='utf-8') as f:
            f.write(self.markdown)

    def wrapper(self):
        self.arg_parser()
        self.parser(self.getter())
        if self.table:
            self.writer()
        self._driver.quit()


if __name__ == '__main__':
    metro = MetroPCS()
    metro.wrapper()
