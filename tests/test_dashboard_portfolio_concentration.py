from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "dashboard-portfolio-concentration.js").read_text(encoding="utf-8")
CSS = (ROOT / "dashboard-portfolio-concentration.css").read_text(encoding="utf-8")
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class DashboardPortfolioConcentrationTests(unittest.TestCase):
    def test_companion_is_reachable_and_offline_capable(self):
        self.assertIn("ensureDashboardPortfolioConcentration", LOADER)
        self.assertIn("dashboard-portfolio-concentration.js?v=1.8", LOADER)
        self.assertIn('"./dashboard-portfolio-concentration.js"', SW)
        self.assertIn('"./dashboard-portfolio-concentration.css"', SW)
        self.assertIn("version:'1.8'", JS)

    def test_concentration_is_market_sleeve_only_and_transparent(self):
        self.assertIn("function marketHoldings", JS)
        self.assertIn("filter(row=>isThemeEligibleAsset(row.asset))", JS)
        self.assertIn("Concentração dos ativos de mercado", JS)
        self.assertIn("Depósitos, obrigações, PPR, imóveis e cripto", JS)
        self.assertIn("dos ativos de mercado", JS)

    def test_concentration_is_direct_and_transparent(self):
        self.assertIn("function concentrationSnapshot", JS)
        self.assertIn("const hhi=weighted.reduce", JS)
        self.assertIn("1/hhi", JS)
        self.assertIn("Top 3", JS)
        self.assertIn("ETFs contam como uma posição neste modo", JS)

    def test_etf_lookthrough_uses_only_observed_holdings_and_keeps_residual(self):
        self.assertIn("function buildLookthrough", JS)
        self.assertIn("top_holdings", JS)
        self.assertIn("holdingPercent", JS)
        self.assertIn("etf-residual", JS)
        self.assertIn("não detalhado", JS)
        self.assertIn("sem dupla contagem", JS)
        self.assertIn("VestraMarketData?.hydrateTicker", JS)
        self.assertIn("function hydrationCandidates", JS)
        self.assertIn("slice(0,24)", JS)
        self.assertIn("i+=6", JS)
        self.assertIn("requestIdleCallback", JS)
        self.assertNotIn("fund_theme", JS)

    def test_concentration_copy_is_plain_language_and_modes_are_clear(self):
        self.assertIn("Concentração das posições", JS)
        self.assertIn("As 3 maiores posições representam", JS)
        self.assertIn(">Posições</button>", JS)
        self.assertIn(">Dentro dos ETFs</button>", JS)
        self.assertIn("posições iguais · índice HHI", JS)
        self.assertIn(".dpc-answer", CSS)

    def test_theme_exposure_is_primary_normalized_and_evidence_based(self):
        self.assertIn("const THEME_RULES", JS)
        self.assertIn("function primaryTheme", JS)
        self.assertIn("function buildThemeExposure", JS)
        self.assertIn("Não classificado", JS)
        self.assertIn("portfolioThemeExposureCard", JS)
        self.assertIn("isThemeEligibleAsset", JS)
        self.assertIn("assetThemeEvidence", JS)
        self.assertIn("marketShare", JS)
        self.assertIn("marketWeight", JS)
        self.assertIn("Ativos de mercado", JS)
        self.assertIn("Depósitos, obrigações, PPR, imóveis e cripto", JS)
        self.assertIn("EXPOSIÇÃO TEMÁTICA", JS)
        self.assertIn("IA & Robótica", JS)
        self.assertIn("Semicondutores", JS)
        self.assertIn("Matérias-primas", JS)
        self.assertNotIn('data-dpc-mode="themes"', JS)
        self.assertNotIn("themeWeights", JS)

    def test_theme_evidence_keeps_contributor_provenance_and_drilldown(self):
        self.assertIn("contributors:new Map()", JS)
        self.assertIn("dpc-theme-chip", JS)
        self.assertIn("COMO SE FORMA", JS)
        self.assertIn("Percentagens grandes = peso no património total", JS)
        self.assertIn("data-dpc-theme", JS)
        self.assertIn("data-dpc-theme-close", JS)
        self.assertIn(".dpc-theme-detail", CSS)

    def test_theme_hydration_has_single_assignment_and_fail_soft_theme_rebuild(self):
        self.assertEqual(JS.count("S.details=details;"), 2)
        self.assertEqual(JS.count("S.themes=buildThemeExposure(assets,details"), 2)
        self.assertIn("}catch(_){", JS)
        self.assertIn("S.themes=buildThemeExposure(assets,details", JS)

    def test_theme_exposure_replaces_class_allocation_card(self):
        self.assertNotIn("function classAllocation", JS)
        self.assertNotIn("portfolioClassAllocationCard", JS)
        self.assertIn("Onde estão as tuas apostas de mercado?", JS)
        self.assertIn("dashboardDistributionCard", INDEX)
        self.assertIn('id="dashboardDistributionCard" hidden', INDEX)
        self.assertIn(".dpc-theme-bar", CSS)
        self.assertIn(".dpc-theme-stats", CSS)

    def test_assets_and_liabilities_do_not_share_analysis_cards(self):
        self.assertIn("portfolioShowsAssets", JS)
        self.assertIn("#segAssets,#segLiabs", JS)
        self.assertIn("document.getElementById(CARD_ID)?.remove()", JS)
        self.assertIn("document.getElementById(THEME_CARD_ID)?.remove()", JS)

    def test_card_is_owned_by_portfolio_view_and_responsive(self):
        self.assertIn("viewAssets", JS)
        self.assertIn("portfolioGlance", JS)
        self.assertNotIn("dashboardPortfolioPulseCard", JS)
        self.assertIn("dpc-mosaic", JS)
        self.assertIn("@media(max-width:560px)", CSS)
        self.assertIn("@media(max-width:360px)", CSS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
