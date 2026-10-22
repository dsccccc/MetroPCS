import argparse
import json
import time
from html import unescape
from pathlib import Path

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
        """Wait for populated product cards, not just the grid's empty shell."""
        for attempt in range(3):
            try:
                self._driver.get(self.APPLE_URL)

                def loaded_families(driver):
                    if 'access denied' in driver.title.lower():
                        raise RuntimeError('Metro blocked the listing request (Access Denied)')
                    return self._parse_families(driver.page_source)

                families = WebDriverWait(self._driver, 30).until(loaded_families)
                print(f'Loaded {len(families)} Apple product families.')
                return families
            except Exception as exc:
                print(f'Listing attempt {attempt + 1}/3 failed: {type(exc).__name__}: {exc}')
                self._save_diagnostics()
                if attempt == 2:
                    raise RuntimeError('Unable to load Apple product names; README was not updated') from exc
                time.sleep(5)

    def _save_diagnostics(self):
        """Keep the failed page available as a GitHub Actions artifact."""
        try:
            directory = Path(self.output_dir or '.') / 'diagnostics'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'listing.html').write_text(self._driver.page_source, encoding='utf-8')
            print(f'Failed page: {self._driver.current_url} ({self._driver.title})')
            self._driver.save_screenshot(str(directory / 'listing.png'))
        except Exception as exc:
            print(f'Could not save diagnostics: {exc}')

    @classmethod
    def _parse_families(cls, html):
        soup = BeautifulSoup(html, features='html.parser')
        families = []
        seen = set()
        for card in soup.select('li[data-upf-product-grid-item], [data-testid="product-card"]'):
            if card.find_parent('template') is not None:
                continue
            brand = cls._visible_text(card, '.upf-productCard__title--brand, [data-testid="product-card-manufacturer"]')
            model = cls._visible_text(card, '.upf-productCard__title--model, [data-testid="product-card-name"]')
            link = next((el for el in card.select('a.upf-productCard__content-link[href], a.product-card__link[href]')
                         if el.find_parent('template') is None and el['href'].strip()), None)
            if not (brand and model and link) or brand.casefold() != 'apple':
                continue
            url = link['href']
            if url in seen:
                continue
            seen.add(url)
            families.append({
                'name': f'{brand} {model}',
                'sku': card.get('data-upf-plp-card-sku') or card.get('data-sku', ''),
                'family_code': card.get('data-upf-plp-card-family-code', ''),
                'url': url,
                'esim': 'eSIM' in (card.get('data-upf-plp-card-filter') or ''),
            })
        return families

    @staticmethod
    def _visible_text(card, selector: str) -> str:
        """First non-empty match that is not inside an unrendered <template> block."""
        for el in card.select(selector):
            if el.find_parent('template') is None:
                text = ' '.join(el.stripped_strings)
                text = ' '.join(text.split())
                if text:
                    return text
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
        variants = self._parse_variants(self._driver.page_source)
        return api_json, variants

    @staticmethod
    def _decode_astro(value):
        """Decode the object/array tags used by Astro's product props."""
        tag, data = value
        if tag == 0:
            if isinstance(data, dict):
                return {key: MetroPCS._decode_astro(item) for key, item in data.items()}
            return data
        if tag == 1:
            return [MetroPCS._decode_astro(item) for item in data]
        raise ValueError(f'Unsupported Astro product data tag: {tag}')

    @classmethod
    def _parse_variants(cls, html):
        soup = BeautifulSoup(html, features='html.parser')
        variants = {}
        legacy = soup.select_one('.upf-skuSelector[data-upf-variants]')
        if legacy:
            for variant in json.loads(unescape(legacy['data-upf-variants'])):
                variants[variant['sku']] = variant
        island = soup.select_one('astro-island[component-url*="ProductDetailPage"][props]')
        if island:
            product = json.loads(island['props'])['product'][1]
            colors = cls._decode_astro(product['colors'])
            storage = cls._decode_astro(product['storage'])
            mapping = cls._decode_astro(product['colorMemorySkuMap'])
            capacities = {item['id']: item['capacity'] for item in storage}
            for color in colors:
                for memory_id, sku in mapping.get(color['skuCode'], {}).items():
                    variants[sku] = {'sku': sku, 'color': color['name'],
                                     'memory': capacities[memory_id]}
        return variants

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
            raise RuntimeError('No products found; README was not updated')
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
        try:
            self.arg_parser()
            self.parser(self.getter())
            if self.table:
                self.writer()
        finally:
            self._driver.quit()


if __name__ == '__main__':
    metro = MetroPCS()
    metro.wrapper()
