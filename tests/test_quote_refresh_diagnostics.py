from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.js"

class QuoteRefreshDiagnosticsTests(unittest.TestCase):
    def test_app_js_is_valid(self):
        subprocess.run(["node", "--check", str(APP)], check=True, cwd=ROOT)

    def test_fallback_attempts_are_measured_without_changing_identity_policy(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("let attempts = 0", text)
        self.assertIn("durationMs: Math.round(performance.now() - startedAt)", text)
        self.assertIn("outErr.quoteAttempts = attempts", text)
        self.assertIn("isQuoteCandidateAcceptable(ref.asset, candidate)", text)
        self.assertIn("for (const candidate of (ref.candidates || []))", text)

    def test_refresh_report_persists_compact_performance_diagnostics(self):
        text = APP.read_text(encoding="utf-8")
        for token in (
            "quotePerformanceRows", "fallbackAssets", "maxCandidateAttempts",
            "meanDurationMs", "slowestAssets", "performance: {"
        ):
            self.assertIn(token, text)
        self.assertIn("com fallback", text)
        self.assertIn("QUOTE_AUTO_REFRESH_STALE_MS = 60 * 1000", text)

    def test_diagnostics_do_not_parallel_race_candidates(self):
        text = APP.read_text(encoding="utf-8")
        self.assertNotIn("Promise.any(ref.candidates", text)
        self.assertNotIn("Promise.race(ref.candidates", text)

if __name__ == "__main__":
    unittest.main(verbosity=2)
