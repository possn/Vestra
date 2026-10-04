import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class RuntimeRegressionTests(unittest.TestCase):

    def test_score_validation_contract_is_shared_by_pipeline_and_production_smoke(self):
        market = (ROOT / ".github" / "workflows" / "update-market-data.yml").read_text(encoding="utf-8")
        smoke = (ROOT / ".github" / "workflows" / "production-smoke.yml").read_text(encoding="utf-8")
        self.assertIn("validate_report_contract(report)", market)
        self.assertIn("Validate published score report contract", smoke)
        self.assertIn("validate_report_contract(report)", smoke)
        self.assertIn("score_validation_report.json", smoke)
        self.assertNotIn("evaluate_report_freshness(report)", market)

    def test_market_pipeline_guards_score_validation_report_before_publish(self):
        workflow = (ROOT / ".github" / "workflows" / "update-market-data.yml").read_text(encoding="utf-8")
        guard_name = "Validate score validation report contract"
        publish_name = "Publish validated market data"
        self.assertIn(guard_name, workflow)
        self.assertIn("evaluate_report_freshness(report)", workflow)
        self.assertIn('"composition_stability" not in model_pack', workflow)
        self.assertLess(workflow.index(guard_name), workflow.index(publish_name))

    def test_chart_stabilization_is_coalesced(self):
        src = (ROOT / "app-ui-core.js").read_text(encoding="utf-8")
        self.assertIn("let chartStabilizeFrame = null;", src)
        self.assertIn("let chartStabilizeTimer = null;", src)
        self.assertIn("cancelAnimationFrame(chartStabilizeFrame)", src)
        self.assertIn("clearTimeout(chartStabilizeTimer)", src)
        self.assertIn("}, 180);", src)
        self.assertNotIn("setTimeout(run, 140);", src)
        self.assertNotIn("setTimeout(run, 420);", src)


    def test_app_module_load_order(self):
        html = read("index.html")
        ordered = [
            "app-utils.js",
            "app-feedback.js",
            "app-storage.js",
            "app-asset-identity.js",
            "app-chart-loader.js",
            "app-ui-core.js",
            "app-broker-normalization.js",
            "app-file-parsing.js",
            "app-broker-parsing-core.js",
            "app-broker-import-loader.js",
            "app-market-client.js",
            "app-quote-errors.js",
            "app-return-assumptions.js",
            "app-financial-engine.js",
            "app.js",
        ]
        positions = []
        for script in ordered:
            pos = html.find(script)
            self.assertGreaterEqual(pos, 0, f"{script} missing from index.html")
            positions.append(pos)
        self.assertEqual(positions, sorted(positions), "app module dependency order changed")
        self.assertNotIn("app-broker-workbook.js", html)
        self.assertNotIn("app-broker-parsers.js", html)
        self.assertNotIn('src="app-broker-identity-data.js', html)
        self.assertNotIn('src="app-xtb-normalization.js', html)
        loader = read("app-broker-import-loader.js")
        self.assertIn("app-broker-identity-data.js?v=1.0", loader)
        self.assertIn("app-xtb-normalization.js?v=1.0", loader)
        self.assertIn("app-broker-workbook.js?v=1.3", loader)
        self.assertIn("app-broker-parsers.js?v=1.4", loader)
        self.assertLess(
            loader.index("app-broker-workbook.js?v=1.3"),
            loader.index("app-broker-parsers.js?v=1.4"),
        )

    def test_all_app_modules_are_syntax_checked_by_ci(self):
        workflow = read(".github/workflows/architecture-invariants.yml")
        modules = [
            "app-utils.js", "app-feedback.js", "app-storage.js", "app-asset-identity.js",
            "app-chart-loader.js", "app-ui-core.js", "app-broker-normalization.js", "app-xtb-normalization.js",
            "app-broker-identity-data.js", "app-file-parsing.js", "app-broker-parsing-core.js",
            "app-broker-import-loader.js", "app-broker-workbook.js", "app-broker-parsers.js", "app-market-client.js",
            "app-quote-errors.js", "app-return-assumptions.js", "app-financial-engine.js",
            "app.js", "market.js", "market-data-loader.js", "market-data-health.js",
            "market-global-search.js", "market-learned-universe.js", "politicians.js", "worker.js",
        ]
        for module in modules:
            self.assertIn(f"node --check {module}", workflow, f"CI does not syntax-check {module}")

    def test_quote_errors_are_inline_not_modal_locked(self):
        quote_ui = read("app-quote-errors.js")
        self.assertIn("showQuoteErrorSheetFromModal", quote_ui)
        self.assertIn("closeQuoteErrorSheet", quote_ui)
        self.assertNotIn("new MutationObserver", quote_ui)
        self.assertIn("vestra:modal-opened", quote_ui)
        self.assertIn("document.body.classList.remove('modal-open')", quote_ui)
        self.assertIn("-webkit-overflow-scrolling:touch", quote_ui)
        self.assertIn("releaseBodyLock(modal)", quote_ui)
        self.assertIn("z-index:1002", quote_ui)

    def test_broker_rebuild_schema_contains_latest_dividend_repair(self):
        app = read("app.js")
        m = re.search(r"BROKER_REBUILD_SCHEMA_VERSION\s*=\s*(\d+)", app)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 45)
        self.assertIn("reconcileBrokerDividends", app)

    def test_dividend_normalization_remains_gross_minus_tax(self):
        norm = read("app-broker-normalization.js")
        self.assertIn("return divFloor(d, parseNum(d.amount) - tax)", norm)
        self.assertIn("d.netAmount = g - tax", norm)
        self.assertIn("reconcileBrokerDividends", norm)

    def test_canonical_broker_quote_repairs_remain_present(self):
        core = read("app-broker-parsing-core.js")
        self.assertIn('"|MPW.US": "MPT"', core)
        self.assertIn('return "AMS.SW"', core)
        self.assertIn('return "EDV.TO"', core)
        self.assertIn('return "NEO.TO"', core)

    def test_worker_is_live_market_only_for_congress(self):
        worker = read("worker.js")
        self.assertIn('"/market"', worker)
        self.assertNotIn('"/congress"', worker)
        self.assertNotIn("bargofinance", worker.lower())

    def test_market_live_overlay_does_not_rerender_open_dossier(self):
        market = read("market.js")
        overlay = read("market-live-overlay.js")
        html = read("index.html")
        sw = read("sw.js")
        self.assertIn("VestraMarketLiveOverlay?.create", market)
        self.assertIn("marketLiveOverlay?.enrichTickerLive", market)
        self.assertIn("marketLiveOverlay?.refreshOpenDossierLiveFields", market)
        self.assertNotIn("Object.assign(s,merge,{_liveUpdated", market)
        for field in ("current_price", "forward_pe", "roe", "revenue_growth", "fcf_yield"):
            self.assertIn(field, overlay)
        self.assertNotIn("marketSheetContent", overlay)
        self.assertNotIn('src="market.js?v=20260831v2"', html)
        self.assertNotIn('src="market-live-overlay.js', html)
        loader = read("market-runtime-loader.js")
        self.assertIn("loadHelper('VestraMarketLiveOverlay', 'market-live-overlay.js?v=1.2')", loader)
        self.assertLess(loader.index("market-live-overlay.js?v=1.2"), loader.index("script.src = 'market.js?v=20260926rotation4';"))
        self.assertIn('"./market-live-overlay.js"', sw)

    def test_non_market_global_click_listeners_are_released(self):
        mobile = read("mobile-ui-refresh.js")
        loader = read("market-runtime-loader.js")
        html = read("index.html")
        self.assertNotIn("document.addEventListener('click'", mobile)
        self.assertIn("vestra:view-rendered", mobile)
        self.assertIn("function captureEarlyModeIntent(event)", loader)
        self.assertIn("document.removeEventListener?.('click', captureEarlyModeIntent, true)", loader)
        self.assertIn("market-runtime-loader.js?v=2.2", html)

    def test_lifecycle_persistence_is_blocked_until_hydration(self):
        app = read("app.js")
        self.assertIn("function saveStateOnLifecycleExit()", app)
        self.assertIn("if (window.__vestraAppHydrated !== true) return false", app)
        self.assertIn('window.addEventListener("pagehide", saveStateOnLifecycleExit)', app)
        self.assertIn('window.addEventListener("beforeunload", saveStateOnLifecycleExit)', app)
        self.assertIn('saveStateOnLifecycleExit();', app)
        self.assertNotIn('window.addEventListener("pagehide", () => saveStateAsync())', app)
        self.assertNotIn('window.addEventListener("beforeunload", () => saveStateAsync())', app)

    def test_storage_contract_is_stable(self):
        storage = read("app-storage.js")
        expected = {
            "STORAGE_KEY": "PF_STATE_V6",
            "DB_NAME": "pf_v6",
            "DB_STORE": "kv",
            "DB_KEY": "state",
        }
        for const_name, value in expected.items():
            pattern = rf"const\s+{const_name}\s*=\s*(['\"])({re.escape(value)})\1\s*;"
            self.assertRegex(storage, pattern, f"storage contract changed: {const_name}")


if __name__ == "__main__":
    unittest.main()
