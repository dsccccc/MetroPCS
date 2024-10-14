import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
from json import loads


class MetroPCS:
    def __init__(self):
        self.BASE_URL = 'https://www.metrobyt-mobile.com/'
        self.APPLE_URL = 'https://www.metrobyt-mobile.com/cell-phones/brand/apple'

        self.urls = []
        self.products = {}

        self.output_dir: str = ''
        self.file_name: str = ''
        self.modes = None
        self.proxy: str = ''
        self.table: bool = True
        self.markdown: str = ''

        self.options = Options()
        self.options.add_argument("--headless")
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.16 (KHTML, like Gecko) "
            "Chrome/110.0.0.0 Safari/537.36"
        )
        self.options.add_argument(f"user-agent={user_agent}")
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])

        self.serverApp = {
            '&q;': '"',
            # 'false': 'False',
            # 'true': 'True',
            # '&l;': '<',
            # '&g;': '>',
        }

        self.service = Service()

        self._driver = webdriver.Chrome(self.options)  # , service=self.service)

    def arg_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--output_dir', type=str, default='./metro/data/', help='Directory of output files.')
        parser.add_argument('--file_name', type=str, default='metro.md', help='Name of output markdown file.')
        parser.add_argument('--modes', type=str, default='["12","13","SE"]', help='Keywords to search for items.')
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
            self._driver = webdriver.Chrome(self.options)

    def getter(self):
        # noinspection PyBroadException
        try:
            self._driver.get(self.APPLE_URL)
            WebDriverWait(self._driver, 20).until(EC.presence_of_element_located(('id', 'serverApp-state')))
            soup = BeautifulSoup(self._driver.page_source, from_encoding='utf-8', features='html.parser')
            print(soup)
        except Exception:
            self._driver.quit()
            time.sleep(5)
            self._driver = webdriver.Chrome(self.options)
            return None
        else:
            return soup.find('script', attrs={'id': 'serverApp-state'}).get_text()

    def parser(self, content):
        data = loads(content.replace('&q;', '"'))
        mappings = data['NGRX_TRANSFER_STATE_KEY']['device-compatibility']['mapping']
        len_name = max(len(mapping['name']) for mapping in mappings)
        print(f'MetroPCS\t{time.strftime("%m/%d/%Y", time.localtime()):{len_name - 16}s}\t'
              f'{"color":16s}\tmemory\teSIM\tprice\t{"status":13s}\t{"Shipping from":10s}\t{"to":10s}')
        self.markdown += (f'|MetroPCS {time.strftime("%m/%d/%Y", time.localtime())}|color|memory|eSIM|price|status'
                          f'|shipping from|shipping to|\n')
        self.markdown += '|:--:' * 8 + '|\n'
        for mapping in mappings:
            name = mapping['name']
            if type(self.modes) is list:
                for mode in self.modes:
                    if mode in name:
                        break
                else:
                    continue
            elif type(self.modes) is str:
                if self.modes not in name:
                    continue
            else:
                print('Invalid keywords!')
            entity = mapping['id']
            skus = data['NGRX_TRANSFER_STATE_KEY']['product-families']['entities'][entity]['skus']
            for sku in skus:
                color = sku['color']
                memory = sku['memory']
                price = sku['frpPrice']['salePrice']
                esim = 'eSIM' in sku['simType']
                status = sku['availability']['availabilityStatus']
                shipping0 = sku['availability']['estimatedShippingFromDateTime']
                shipping1 = sku['availability']['estimatedShippingToDateTime']
                deal = max([promotion['discountValue']['amount'] for promotion in sku['availableCartPromotions']])
                print(f'{name:{len_name}s}\t{color:16s}\t{memory}\t{esim}\t{price - deal:.2f}\t'
                      f'{status:13s}\t{shipping0}\t{shipping1}')
                self.markdown += f'|{name}|{color}|{memory}|{esim}|{price - deal:.2f}|{status}|{shipping0}|{shipping1}|\n'

    def writer(self):
        with open(self.file_name, 'w+', encoding='utf-8') as f:
            f.write('# MetroPCS\n')
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
