from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")

class PortfolioTopPositionsTests(unittest.TestCase):
    def test_default_portfolio_list_is_top_five(self):
        self.assertIn("Mostrar 5 posições principais por defeito", APP)
        self.assertIn("const LIMIT = 5;", APP)
        self.assertIn("Ver todas (${src.length})", APP)
        self.assertIn('? "Mostrar menos"', APP)

    def test_portfolio_copy_matches_compact_list(self):
        self.assertIn('id="itemsTitle">Posições principais<', INDEX)
        self.assertIn("Top 5 por valor · pesquisa e filtros para ver o resto.", INDEX)
        self.assertIn("app.js?v=20260923v13", INDEX)

if __name__ == "__main__":
    unittest.main(verbosity=2)
