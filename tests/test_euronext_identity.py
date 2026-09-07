import unittest

from scripts.euronext_identity import _extract_exact_isin, _parts


class EuronextIdentityTests(unittest.TestCase):
    def test_supported_suffix_maps_to_exact_market(self):
        self.assertEqual(_parts('AIR.PA'), ('AIR', 'Euronext Paris'))
        self.assertEqual(_parts('GALP.LS'), ('GALP', 'Euronext Lisbon'))
        self.assertIsNone(_parts('AAPL'))

    def test_exact_symbol_and_market_only(self):
        html = '''<table><thead><tr><th>Name</th><th>ISIN</th><th>Symbol</th><th>Market</th></tr></thead>
        <tbody>
        <tr><td>Galp</td><td>PTGAL0AM0009</td><td>GALP</td><td>Euronext Lisbon</td></tr>
        <tr><td>Other</td><td>FR0000000001</td><td>GALP</td><td>Euronext Paris</td></tr>
        </tbody></table>'''
        self.assertEqual(_extract_exact_isin(html, 'GALP', 'Euronext Lisbon'), 'PTGAL0AM0009')
        self.assertIsNone(_extract_exact_isin(html, 'GAL', 'Euronext Lisbon'))

    def test_ambiguous_exact_matches_fail_closed(self):
        html = '''<table><tr><th>ISIN</th><th>Symbol</th><th>Market</th></tr>
        <tr><td>PTGAL0AM0009</td><td>GALP</td><td>Euronext Lisbon</td></tr>
        <tr><td>PTGAL0AM0017</td><td>GALP</td><td>Euronext Lisbon</td></tr></table>'''
        self.assertIsNone(_extract_exact_isin(html, 'GALP', 'Euronext Lisbon'))


if __name__ == '__main__':
    unittest.main()
