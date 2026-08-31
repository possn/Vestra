from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "market.js"


class Low52UiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MARKET.read_text(encoding="utf-8")

    def test_visual_shortlist_is_equities_only_and_within_five_percent(self):
        self.assertIn("M.stocks.filter(s=>!isFund(s))", self.source)
        self.assertIn("x.stats.above>=-0.5 && x.stats.above<=5", self.source)
        self.assertIn("Sem empresas até 5% do mínimo de 52 semanas.", self.source)

    def test_visual_shortlist_can_use_compact_52_week_bounds(self):
        self.assertIn("n(s?.low52_price_low)??n(s?.fifty_two_week_low)", self.source)
        self.assertIn("n(s?.low52_price_high)??n(s?.fifty_two_week_high)", self.source)

    def test_low52_rows_keep_standard_dossier_click_contract(self):
        self.assertIn("return renderRow(s,meta);", self.source)
        self.assertIn("const row=e.target.closest('[data-market-ticker]')", self.source)
        self.assertIn("openTicker(row.dataset.marketTicker)", self.source)

    def test_intelligence_and_visual_thresholds_are_intentionally_distinct(self):
        engine = (ROOT / "scripts" / "low52_intelligence.py").read_text(encoding="utf-8")
        self.assertIn('near_low = pos["above_low_pct"] <= 10.0 + 1e-9', engine)
        self.assertIn("x.stats.above>=-0.5 && x.stats.above<=5", self.source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
