from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCH = (ROOT / ".github" / "workflows" / "architecture-invariants.yml").read_text(encoding="utf-8")
MARKET = (ROOT / ".github" / "workflows" / "update-market-data.yml").read_text(encoding="utf-8")

CRITICAL = (
    "scripts/capital_risk.py",
    "scripts/capital_risk_scan_order.py",
    "scripts/insiders.py",
    "scripts/insider_runtime_metrics.py",
    "scripts/insider_archives_runtime.py",
)


class SecInsiderCiCoverageTests(unittest.TestCase):
    def test_architecture_ci_triggers_and_compiles_critical_modules(self):
        for path in CRITICAL:
            self.assertGreaterEqual(ARCH.count(path), 3, path)

    def test_production_preflight_compiles_critical_modules(self):
        for path in CRITICAL:
            self.assertIn(path, MARKET)

    def test_pipeline_artifact_keeps_risk_and_insider_caches_for_diagnostics(self):
        self.assertIn("data/capital_risk_cache.json", MARKET)
        self.assertIn("data/insider_filings_cache.json", MARKET)


if __name__ == "__main__":
    unittest.main(verbosity=2)
