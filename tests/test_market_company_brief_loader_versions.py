from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketCompanyBriefLoaderVersionTests(unittest.TestCase):
    def test_dossier_controls_fallback_tracks_canonical_version(self):
        company = (ROOT / 'market-company-brief.js').read_text(encoding='utf-8')
        dossier = (ROOT / 'market-dossier-controls.js').read_text(encoding='utf-8')
        self.assertIn("market-dossier-controls.js?v=1.4", company)
        self.assertIn("version: '1.4'", dossier)
        self.assertNotIn("market-dossier-controls.js?v=1.1", company)


if __name__ == '__main__':
    unittest.main(verbosity=2)
