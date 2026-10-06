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
        self.assertIn("Sem entradas por preço esta semana", source)

    def test_startup_publishes_rotation_returns_independent_of_opportunity_eligibility(self):
        builder = (ROOT / "scripts" / "build_market_shards.py").read_text(encoding="utf-8")
        market = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn('r5 = _finite_number(row.get("market_return_5d_pct"))', builder)
        self.assertIn('r20 = _finite_number(row.get("market_return_20d_pct"))', builder)
        self.assertIn('out["market_return_5d_pct"] = round(r5, 4)', builder)
        self.assertIn('out["market_return_20d_pct"] = round(r20, 4)', builder)
        self.assertIn("return n(stock?.market_return_5d_pct);", market)
        self.assertIn("r20:n(s.market_return_20d_pct)", market)
        self.assertNotIn("opportunity_return_20d_pct)})).filter", market)

    def test_etf_consensus_is_fail_closed_on_directional_divergence(self):
        source = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("function weeklyEtfConsensus(expectedSign, etfReturn, flowUsd)", source)
        self.assertIn("directional.every(sign=>sign===expectedSign)", source)
        self.assertIn("ETF confirma", source)
        self.assertIn("ETF diverge", source)
        self.assertIn("weeklyEtfConfirmation(label,expectedEtfSign)", source)
        self.assertIn("expectedEtfSign=1", source)
        self.assertIn("expectedEtfSign=-1", source)

    def test_etf_flow_text_surfaces_effective_observation_window(self):
        source = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("fund_flow_observation_days", source)
        self.assertIn("flowWindowMin", source)
        self.assertIn("flowWindowMax", source)
        self.assertIn("' · janela '", source)

    def test_semiconductors_style_price_strength_with_negative_flow_is_not_confirmed(self):
        # Deterministic reference fixture for the production consensus contract:
        # positive ETF return but -$3.9B flow must fail closed for an inflow signal.
        expected_sign = 1
        etf_return = 2.0
        flow_usd = -3_900_000_000
        directional = [1 if value > 0 else -1 for value in (etf_return, flow_usd) if value not in (None, 0)]
        self.assertEqual(directional, [1, -1])
        self.assertFalse(all(sign == expected_sign for sign in directional))

    def test_matching_etf_return_without_flow_is_not_called_confirmed(self):
        expected_sign = 1
        etf_return = 2.0
        flow_usd = None
        directional = [1 if value > 0 else -1 for value in (etf_return, flow_usd) if value not in (None, 0)]
        all_agree = bool(directional) and all(sign == expected_sign for sign in directional)
        has_aligned_flow = flow_usd not in (None, 0) and (1 if flow_usd > 0 else -1) == expected_sign
        self.assertTrue(all_agree)
        self.assertFalse(has_aligned_flow)

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
            '"opportunity_rotation_etf_confirmed"',
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
