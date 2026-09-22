from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "dashboard-portfolio-concentration.js").read_text(encoding="utf-8")
CSS = (ROOT / "dashboard-portfolio-concentration.css").read_text(encoding="utf-8")
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


class DashboardPortfolioConcentrationTests(unittest.TestCase):
    def test_companion_is_reachable_and_offline_capable(self):
        self.assertIn("ensureDashboardPortfolioConcentration", LOADER)
        self.assertIn("dashboard-portfolio-concentration.js?v=1.3", LOADER)
        self.assertIn('"./dashboard-portfolio-concentration.js"', SW)
        self.assertIn('"./dashboard-portfolio-concentration.css"', SW)
        self.assertIn("version:'1.3'", JS)

    def test_concentration_is_direct_and_transparent(self):
        self.assertIn("function concentrationSnapshot", JS)
        self.assertIn("const hhi=weighted.reduce", JS)
        self.assertIn("1/hhi", JS)
        self.assertIn("Top 3", JS)
        self.assertIn("ETFs contam como uma posição única", JS)

    def test_etf_lookthrough_uses_only_observed_holdings_and_keeps_residual(self):
        self.assertIn("function buildLookthrough", JS)
        self.assertIn("top_holdings", JS)
        self.assertIn("holdingPercent", JS)
        self.assertIn("etf-residual", JS)
        self.assertIn("não detalhado", JS)
        self.assertIn("Sem dupla contagem", JS)
        self.assertIn("VestraMarketData?.hydrateTicker", JS)
        self.assertIn("requestIdleCallback", JS)
        self.assertNotIn("fund_theme", JS)

    def test_theme_mode_is_primary_normalized_and_evidence_based(self):
        self.assertIn("const THEME_RULES", JS)
        self.assertIn("function primaryTheme", JS)
        self.assertIn("function buildThemeExposure", JS)
        self.assertIn("Não classificado", JS)
        self.assertIn("classificação normalizada a 100%", JS)
        self.assertIn("cada exposição só entra num tema primário", JS)
        self.assertIn("data-dpc-mode=\"themes\"", JS)
        self.assertNotIn("themeWeights", JS)

    def test_theme_evidence_keeps_contributor_provenance_and_drilldown(self):
        self.assertIn("contributors:new Map()", JS)
        self.assertIn("dpc-theme-chip", JS)
        self.assertIn("COMO SE FORMA", JS)
        self.assertIn("Contributos calculados sobre o património total", JS)
        self.assertIn("data-dpc-theme", JS)
        self.assertIn("data-dpc-theme-close", JS)
        self.assertIn(".dpc-theme-detail", CSS)

    def test_theme_hydration_has_single_assignment_and_fail_soft_theme_rebuild(self):
        self.assertEqual(JS.count("S.details=details;"), 2)
        self.assertEqual(JS.count("S.themes=buildThemeExposure(assets,details"), 2)
        self.assertIn("}catch(_){", JS)
        self.assertIn("S.themes=buildThemeExposure(assets,details", JS)

    def test_card_uses_portfolio_pulse_anchor_and_responsive_mosaic(self):
        self.assertIn("dashboardPortfolioPulseCard", JS)
        self.assertIn("dpc-mosaic", JS)
        self.assertIn("@media(max-width:560px)", CSS)
        self.assertIn("@media(max-width:360px)", CSS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
