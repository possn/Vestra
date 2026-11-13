"""The editorial Home and Carteira must display identical, current financial totals."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
HOME = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class FinancialHomeSyncContract(unittest.TestCase):
    def test_one_canonical_valuation_and_passive_income_snapshot(self):
        snapshot = APP.split("window.VestraFinancialTotals = () => {", 1)[1].split("\n};", 1)[0]
        for field in ("net:t.net", "assetsTotal:t.assetsTotal", "liabsTotal:t.liabsTotal",
                      "passiveAnnual:getDisplayedPassiveAnnual(t)",
                      "passiveMonthly:getDisplayedPassiveAnnual(t)/12"):
            self.assertIn(field, snapshot)
        glance = APP.split("function renderPortfolioGlance() {", 1)[1].split(
            "\nfunction normalizePortfolioEquityClass", 1)[0]
        self.assertIn("const canonicalTotals = calcTotals();", glance)
        self.assertIn("canonicalTotals.assetsTotal", glance)
        self.assertIn("getDisplayedPassiveAnnual(canonicalTotals)", glance)
        self.assertNotIn("src.reduce((sum, x) => sum + (getAssetPassiveRatePct", glance)

    def test_home_never_uses_unrendered_dom_as_financial_truth(self):
        sync = HOME.split("function syncWealthHero(host) {", 1)[1].split(
            "\n  function init()", 1)[0]
        self.assertIn("window.VestraFinancialTotals?.()", sync)
        self.assertIn("totals.assetsTotal", sync)
        self.assertIn("totals.passiveMonthly", sync)
        self.assertNotIn("document.getElementById(id)?.textContent", sync)
        self.assertNotIn("'portfolioMonthlyValue'", sync)
        self.assertNotIn("'kpiPassiveMonthly'", sync)

    def test_quote_refresh_notifies_home_after_persisted_state_update(self):
        refresh = APP.split("async function refreshLiveQuotesCore(options = {}) {", 1)[1].split(
            "\n/* ───", 1)[0]
        self.assertIn("await saveStateAsync();", refresh)
        self.assertIn("renderAll();", refresh)
        self.assertIn('new CustomEvent("vestra:portfolio-totals-updated"', refresh)
        self.assertIn('source: "quote-refresh"', refresh)
        self.assertLess(refresh.index("await saveStateAsync();"),
                        refresh.index('new CustomEvent("vestra:portfolio-totals-updated"'))
        self.assertIn("window.addEventListener('vestra:portfolio-totals-updated'", HOME)

    def test_manual_asset_and_liability_changes_refresh_home_totals(self):
        listener = HOME.split("window.addEventListener('vestra:local-state-writing'", 1)[1].split("\n    });", 1)[0]
        self.assertIn('syncWealthHero(host);', listener)
        self.assertLess(listener.index('syncWealthHero(host);'), listener.index('lastDecision = null;'))

    def test_quote_refresh_does_not_claim_fresh_prices_without_success(self):
        view = APP.split("function renderQuoteSyncStatus() {", 1)[1].split(
            "\nfunction updateQuoteButtonStaleness()", 1)[0]
        self.assertIn('const acceptedQuotes = report ?', view)
        self.assertIn('acceptedQuotes === 0', view)
        self.assertIn('noAcceptedQuotes ? "Sem cotações atualizadas"', view)
        self.assertIn('partialRefresh ? "Atualização parcial"', view)
        self.assertIn('failedQuotes > 0 || noAcceptedQuotes', view)
        self.assertIn('skippedQuotes', view)

    def test_iphone_gets_new_versioned_runtime_urls(self):
        self.assertRegex(INDEX, r'app\.js\?v=[^"]+rev=20261109-quote-refresh-truth')
        self.assertRegex(INDEX, r'vestra-intelligence-home\.js\?v=[^"]+rev=20261109-financial-sync')


if __name__ == "__main__":
    unittest.main()
