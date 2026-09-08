import unittest

from scripts.esef_coverage_audit import build_audit, suffix_for


class EsefCoverageAuditTests(unittest.TestCase):
    def test_suffix_matching_is_exact(self):
        self.assertEqual(suffix_for('GALP.LS'), '.LS')
        self.assertEqual(suffix_for('AIR.PA'), '.PA')
        self.assertIsNone(suffix_for('AAPL'))

    def test_builds_identity_funnel_without_network_or_fuzzy_matching(self):
        rows = [
            {'ticker': 'GALP.LS', 'quote_type': 'EQUITY', 'isin': 'PTGAL0AM0009', 'lei': '549300...', 'esef_enriched': True, 'isin_source': 'Euronext official equities list'},
            {'ticker': 'AIR.PA', 'quote_type': 'EQUITY', 'isin': 'NL0000235190', 'lei': '', 'esef_enriched': False, 'isin_source': 'Yahoo Finance'},
            {'ticker': 'NOVO-B.CO', 'quote_type': 'EQUITY'},
            {'ticker': 'EXAMPLE.PA', 'quote_type': 'ETF', 'isin': 'FR0000000000', 'lei': 'X'},
            {'ticker': 'AAPL', 'quote_type': 'EQUITY', 'isin': 'US0378331005'},
        ]
        audit = build_audit(rows)
        self.assertEqual(audit['totals']['eligible'], 3)
        self.assertEqual(audit['totals']['with_isin'], 2)
        self.assertEqual(audit['totals']['with_lei'], 1)
        self.assertEqual(audit['totals']['esef_enriched'], 1)
        self.assertEqual(audit['totals']['missing_isin'], 1)
        self.assertEqual(audit['totals']['isin_without_lei'], 1)
        self.assertEqual(audit['by_suffix']['.LS']['country'], 'PT')
        self.assertEqual(audit['isin_sources']['Euronext official equities list'], 1)


if __name__ == '__main__':
    unittest.main()
