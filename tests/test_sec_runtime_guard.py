import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    sys.modules["requests"] = requests_stub

import sec_endpoint_probe as probe


class SecRuntimeGuardTests(unittest.TestCase):
    def _report(self, status):
        outcome = {"status": status, "ok": 200 <= status < 300}
        sentinels = {
            ticker: {
                "cik": cik,
                "companyfacts": dict(outcome),
                "submissions": dict(outcome),
            }
            for ticker, cik in (("AAPL", 320193), ("MSFT", 789019), ("NVDA", 1045810))
        }
        return {
            "sentinels": sentinels,
            "summary": {"http_ok": 6 if 200 <= status < 300 else 0},
        }

    def test_reachable_companyfacts_exports_runtime_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "github_env"
            blocked = probe.apply_runtime_guard(
                self._report(200),
                env_path=env_path,
                user_agent="Vestra-Test/1.0 contact@example.com",
            )
            self.assertFalse(blocked)
            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                "SEC_USER_AGENT=Vestra-Test/1.0 contact@example.com\n",
            )

    def test_broad_403_disables_companyfacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "github_env"
            blocked = probe.apply_runtime_guard(
                self._report(403),
                env_path=env_path,
                user_agent="Vestra-Test/1.0 contact@example.com",
            )
            self.assertTrue(blocked)
            self.assertEqual(env_path.read_text(encoding="utf-8"), "SEC_USER_AGENT=\n")

    def test_non_403_failure_does_not_disable_companyfacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "github_env"
            blocked = probe.apply_runtime_guard(
                self._report(500),
                env_path=env_path,
                user_agent="Vestra-Test/1.0 contact@example.com",
            )
            self.assertFalse(blocked)
            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                "SEC_USER_AGENT=Vestra-Test/1.0 contact@example.com\n",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
