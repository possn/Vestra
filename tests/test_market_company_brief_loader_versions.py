from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketCompanyBriefLoaderVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.company = (ROOT / 'market-company-brief.js').read_text(encoding='utf-8')
        cls.company_css = (ROOT / 'market-company-brief.css').read_text(encoding='utf-8')
        cls.dossier = (ROOT / 'market-dossier-controls.js').read_text(encoding='utf-8')
        cls.sw = (ROOT / 'sw.js').read_text(encoding='utf-8')

    def test_dossier_controls_fallback_tracks_canonical_version(self):
        self.assertIn("market-dossier-controls.js?v=1.4", self.company)
        self.assertIn("version: '1.4'", self.dossier)
        self.assertNotIn("market-dossier-controls.js?v=1.1", self.company)

    def test_company_brief_presentation_has_static_css_owner(self):
        self.assertIn("market-company-brief.css?v=1.0", self.company)
        self.assertNotIn("document.createElement('style')", self.company)
        self.assertNotIn('style.textContent', self.company)
        self.assertIn('.market-row__description{', self.company_css)
        self.assertIn('.market-company-brief{', self.company_css)
        self.assertIn('"./market-company-brief.css"', self.sw)
        self.assertIn('vestra-cache-v138', self.sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
