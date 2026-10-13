from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"market-opportunities.js").read_text(encoding="utf-8")
CSS=(ROOT/"market-opportunities.css").read_text(encoding="utf-8")

class Low52ContrastTests(unittest.TestCase):
    def test_contrast_scope_follows_selected_lens(self):
        self.assertIn("section.classList.toggle('vestra-low52-contrast',activeLens==='low52')",JS)

    def test_legibility_contract_covers_headers_and_tickers(self):
        for selector in ("market-section__head h3","market-section__head p","market-row__ticker","market-row__name","market-row__description","ux453-thesis"):
            self.assertIn(selector,CSS)
        self.assertIn("background:#f1f0eb!important",CSS)
        self.assertIn("background:#fffefa!important",CSS)
        self.assertIn("color:var(--low52-ink)!important",CSS)
        self.assertIn("opacity:1!important",CSS)

if __name__=="__main__":
    unittest.main()
