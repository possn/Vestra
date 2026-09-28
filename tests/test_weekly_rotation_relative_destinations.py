from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WeeklyRotationRelativeDestinationTests(unittest.TestCase):
    def test_rotation_surfaces_relative_destinations_when_absolute_inflows_are_absent(self):
        source = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("const medianRank=rotationMedian(rows.map(r=>r.rank));", source)
        self.assertIn("const relativeDestinations=!inflows.length", source)
        self.assertIn("A ganhar força relativa", source)
        self.assertIn("não implica entrada líquida", source)
        self.assertIn("Mais resiliente · ainda negativo", source)
        self.assertIn("Sem entradas absolutas confirmadas esta semana", source)

    def test_startup_keeps_rotation_states_but_drops_verbose_opportunity_diagnostics(self):
        source = (ROOT / "scripts" / "build_market_shards.py").read_text(encoding="utf-8")
        for token in (
            '"opportunity_rotation_theme"',
            '"opportunity_rotation_signal"',
            '"opportunity_market_regime"',
            '"opportunity_event_risk"',
            '"opportunity_revision_evidence"',
            '"opportunity_valuation_evidence"',
            '"opportunity_return_5d_pct"',
            '"opportunity_return_20d_pct"',
        ):
            self.assertIn(token, source)
        for token in (
            '"opportunity_upside_reasons"',
            '"opportunity_rotation_breadth_pct"',
            '"opportunity_rotation_return_5d_pct"',
            '"opportunity_rotation_etf_evidence_count"',
            '"opportunity_market_regime_source"',
            '"opportunity_market_regime_evidence_count"',
            '"opportunity_revision_evidence_age_days"',
            '"opportunity_revision_evidence_coverage_pct"',
            '"opportunity_revision_evidence_confidence"',
            '"opportunity_revision_evidence_refresh_state"',
            '"opportunity_valuation_method_count"',
            '"opportunity_valuation_dispersion_pct"',
            '"opportunity_event_risk_days"',
            '"opportunity_event_risk_date"',
            '"opportunity_event_risk_source"',
        ):
            self.assertNotIn(token, source.split("INDEX_KEYS = {",1)[1].split("}",1)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
