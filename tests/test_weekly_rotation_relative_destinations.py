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
        self.assertIn("Sem entradas confirmadas por fluxo esta semana", source)

    def test_confirmed_rotation_requires_etf_flow_alignment(self):
        source = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("function rotationConfirmedDirection(r)", source)
        self.assertIn("const inflows=rows.filter(r=>rotationConfirmedDirection(r)===1)", source)
        self.assertIn("rotationConfirmedDirection(r)===-1", source)
        self.assertIn("Sinais em conflito", source)
        self.assertIn("market-rotation-conflicts", source)
        self.assertIn("Preço/breadth e ETF flow apontam em sentidos opostos", source)
        self.assertIn("Sem entradas confirmadas por fluxo esta semana", source)
        self.assertIn("Sem saídas confirmadas por fluxo esta semana", source)
        self.assertIn("Preço forte · flow vendedor", source)
        self.assertIn("Preço fraco · flow comprador", source)

    def test_startup_publishes_rotation_returns_independent_of_opportunity_eligibility(self):
        builder = (ROOT / "scripts" / "build_market_shards.py").read_text(encoding="utf-8")
        market = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn('out["market_return_5d_pct"] = r5', builder)
        self.assertIn('out["market_return_20d_pct"] = r20', builder)
        self.assertIn("const marketReturn=n(stock?.market_return_5d_pct);", market)
        self.assertIn("n(s.market_return_20d_pct)??n(s.opportunity_return_20d_pct)", market)

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
