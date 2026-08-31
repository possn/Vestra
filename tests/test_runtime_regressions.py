import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class RuntimeRegressionTests(unittest.TestCase):
    def test_app_module_load_order(self):
        html = read("index.html")
        ordered = [
            "app-utils.js",
            "app-feedback.js",
            "app-storage.js",
            "app-asset-identity.js",
            "app-ui-core.js",
            "app-broker-normalization.js",
            "app-xtb-normalization.js",
            "app-broker-identity-data.js",
            "app-broker-parsing-core.js",
            "app-file-parsing.js",
            "app-broker-workbook.js",
            "app-broker-parsers.js",
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

    def test_all_app_modules_are_syntax_checked_by_ci(self):
        workflow = read(".github/workflows/architecture-invariants.yml")
        modules = [
            "app-utils.js", "app-feedback.js", "app-storage.js", "app-asset-identity.js",
            "app-ui-core.js", "app-broker-normalization.js", "app-xtb-normalization.js",
            "app-broker-identity-data.js", "app-broker-parsing-core.js", "app-file-parsing.js",
            "app-broker-workbook.js", "app-broker-parsers.js", "app-market-client.js",
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
        self.assertIn("MutationObserver", quote_ui)
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
        self.assertIn("refreshOpenDossierLiveFields", market)
        self.assertIn('data-live-field="current_price"', market)
        self.assertIn('data-live-field="forward_pe"', market)
        self.assertIn('data-live-field="roe"', market)
        self.assertIn('data-live-field="revenue_growth"', market)
        self.assertIn('data-live-field="fcf_yield"', market)

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
