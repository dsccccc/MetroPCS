import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

from src.MetroPCS import MetroPCS
from script.worker import replacer


CARD = '''<li data-upf-product-grid-item data-upf-plp-card-filter="eSIM">
<template><span class="upf-productCard__title--brand">Wrong</span>
<span class="upf-productCard__title--model">Placeholder</span>
<a class="upf-productCard__content-link" href="/wrong"></a></template>
<span class="upf-productCard__title--brand"> Apple </span>
<span class="upf-productCard__title--model">iPhone <span>16</span> Pro</span>
<a class="upf-productCard__content-link" href="/cell-phone/apple-iphone-16-pro"></a>
</li>'''


class ScraperTests(unittest.TestCase):
    def scraper(self):
        scraper = MetroPCS.__new__(MetroPCS)
        scraper._driver = Mock()
        scraper.APPLE_URL = 'https://example.test/apple'
        scraper.markdown = ''
        scraper.max_price = 500.0
        return scraper

    def test_names_ignore_templates_preserve_spaces_and_deduplicate(self):
        families = MetroPCS._parse_families('<template>' + CARD + '</template>' + CARD * 2)
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]['name'], 'Apple iPhone 16 Pro')
        self.assertEqual(families[0]['url'], '/cell-phone/apple-iphone-16-pro')

    def test_current_svelte_product_card(self):
        html = (Path(__file__).parent / 'fixtures/product-card.html').read_text()
        families = MetroPCS._parse_families(html)
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]['name'], 'Apple iPhone 16e')
        self.assertEqual(families[0]['sku'], '195950051681')
        self.assertEqual(families[0]['url'], '/cell-phone/apple-iphone-16e')
        self.assertEqual(MetroPCS._parse_families(html.replace('>Apple<', '>Samsung<')), [])

    def test_current_variant_mapping(self):
        html = (Path(__file__).parent / 'fixtures/product-detail.html').read_text()
        variants = MetroPCS._parse_variants(html)
        self.assertEqual(variants, {
            '195950642834': {'sku': '195950642834', 'color': 'Lavender', 'memory': '256GB'},
            '195950642803': {'sku': '195950642803', 'color': 'Black', 'memory': '256GB'},
        })

    def test_legacy_variant_mapping(self):
        html = """<div class="upf-skuSelector" data-upf-variants='[
            {"sku":"123", "color":"Black", "memory":"128GB"}]'></div>"""
        self.assertEqual(MetroPCS._parse_variants(html)['123']['memory'], '128GB')

    def test_waits_for_populated_names(self):
        scraper = self.scraper()
        scraper._driver.title = 'Phones'
        type(scraper._driver).page_source = PropertyMock(
            side_effect=['<li data-upf-product-grid-item></li>', CARD])
        self.assertEqual(scraper._get_families()[0]['name'], 'Apple iPhone 16 Pro')

    @patch('src.MetroPCS.time.sleep')
    def test_blocked_page_retries_and_raises(self, sleep):
        scraper = self.scraper()
        scraper._driver.title = 'Access Denied'
        scraper._save_diagnostics = Mock()
        with self.assertRaisesRegex(RuntimeError, 'Unable to load Apple product names'):
            scraper._get_families()
        self.assertEqual(scraper._driver.get.call_count, 3)
        self.assertEqual(scraper._save_diagnostics.call_count, 3)

    def test_empty_results_fail_and_close_browser(self):
        scraper = self.scraper()
        scraper.arg_parser = Mock()
        scraper.getter = Mock(return_value=[])
        with self.assertRaisesRegex(RuntimeError, 'No products found'):
            scraper.wrapper()
        scraper._driver.quit.assert_called_once()

    def test_empty_output_preserves_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'README.md'
            output.write_text('existing products')
            with self.assertRaises(ValueError):
                replacer('', output_file=output)
            self.assertEqual(output.read_text(), 'existing products')

    def test_price_filter_excludes_boundary_and_higher_prices(self):
        scraper = self.scraper()
        rows = [dict(name=f'Phone {price}', color='Black', memory='128GB',
                     esim=True, price=price, status='AVAILABLE', shipping0='', shipping1='')
                for price in [0, 499.99, 500, 500.01]]
        scraper.parser(rows)
        self.assertIn('|Phone 0|', scraper.markdown)
        self.assertIn('|Phone 499.99|', scraper.markdown)
        self.assertNotIn('|Phone 500|', scraper.markdown)
        self.assertNotIn('|Phone 500.01|', scraper.markdown)
        scraper.markdown = ''
        scraper.max_price = 600
        scraper.parser(rows)
        self.assertIn('|Phone 500.01|', scraper.markdown)

    def test_no_price_matches_is_not_a_scrape_failure(self):
        scraper = self.scraper()
        scraper.parser([{'name': 'Expensive phone', 'price': 999.99}])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'README.md'
            replacer(scraper.markdown, output_file=output)
            self.assertIn('No products match the price filter.', output.read_text())

    def test_price_argument_default_override_and_validation(self):
        for arguments, expected in [([], 500), (['--max_price', '250.50'], 250.50)]:
            with patch('sys.argv', ['worker'] + arguments):
                scraper = self.scraper()
                scraper.arg_parser()
                self.assertEqual(scraper.max_price, expected)
        for invalid in ['0', '-1', 'nan', 'inf', 'abc']:
            with self.subTest(invalid=invalid), patch('sys.argv', ['worker', '--max_price', invalid]):
                with patch('sys.stderr'), self.assertRaises(SystemExit):
                    self.scraper().arg_parser()

    def test_product_name_reaches_readme(self):
        scraper = self.scraper()
        family = MetroPCS._parse_families(CARD)[0]
        scraper.parser([dict(name=family['name'], color='Black', memory='128GB',
                             esim=True, price=99.99, status='AVAILABLE', shipping0='', shipping1='')])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'README.md'
            replacer(scraper.markdown, output_file=output)
            self.assertIn('|Apple iPhone 16 Pro|Black|128GB|', output.read_text())


if __name__ == '__main__':
    unittest.main()
