import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.derived_fundamentals import enrich

ROOT = Path(__file__).resolve().parents[1]


def model(**overrides):
    base = dict(
        quote_type="EQUITY",
        market_cap=800.0,
        quarterly_net_income=[
            {"date":"2026-06-30","value":10.0},
            {"date":"2026-03-31","value":10.0},
            {"date":"2025-12-31","value":10.0},
            {"date":"2025-09-30","value":10.0},
        ],
        trailing_pe=None,
        enterprise_to_ebitda=None,
        total_debt=200.0,
        total_cash=100.0,
        ebitda=90.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class DerivedFundamentalsTests(unittest.TestCase):
    def test_derives_pe_from_complete_ttm_net_income(self):
        m = model()
        enrich([m])
        self.assertAlmostEqual(m.trailing_pe, 20.0)
        self.assertIn("trailing_pe", m.derived_metrics)

    def test_requires_four_complete_quarters_for_pe(self):
        m = model(quarterly_net_income=[{"date":"2026-06-30","value":10.0}] * 3)
        enrich([m])
        self.assertIsNone(m.trailing_pe)

    def test_derives_ev_ebitda_only_with_complete_capital_structure(self):
        m = model()
        enrich([m])
        self.assertAlmostEqual(m.enterprise_to_ebitda, 10.0)
        self.assertIn("enterprise_to_ebitda", m.derived_metrics)

        missing_cash = model(total_cash=None)
        enrich([missing_cash])
        self.assertIsNone(missing_cash.enterprise_to_ebitda)

    def test_never_overwrites_observed_metrics(self):
        m = model(trailing_pe=17.5, enterprise_to_ebitda=8.25)
        enrich([m])
        self.assertEqual(m.trailing_pe, 17.5)
        self.assertEqual(m.enterprise_to_ebitda, 8.25)
        self.assertFalse(getattr(m, "derived_metrics", []))

    def test_pipeline_runs_derivation_before_scoring_and_keeps_provenance(self):
        run = (ROOT / "scripts" / "run.py").read_text(encoding="utf-8")
        self.assertIn("from derived_fundamentals import enrich as enrich_derived_fundamentals", run)
        self.assertLess(run.index("raw = enrich_derived_fundamentals(raw)"), run.index("scored = score_universe(raw)"))
        self.assertIn('row["derived_metrics"]', run)
        self.assertIn("Calculated only from observed inputs", run)


if __name__ == "__main__":
    unittest.main()
