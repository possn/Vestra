import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

sys.modules.setdefault("yfinance", types.SimpleNamespace(Ticker=lambda ticker: None))
MODULE_PATH = SCRIPTS / "analyst.py"
spec = importlib.util.spec_from_file_location("analyst_snapshot_loader_test", MODULE_PATH)
analyst = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analyst
spec.loader.exec_module(analyst)


class AnalystPreviousSnapshotLoaderTests(unittest.TestCase):
    def test_loader_reads_only_validated_prefixed_analyst_fields(self):
        payload = {
            "generated_at": "2026-09-05T21:02:16+00:00",
            "stocks": [
                {
                    "ticker": "AAA",
                    "analyst_status": "ok",
                    "analyst_coverage_pct": 66.7,
                    "analyst_eps_next_q": 1.25,
                },
                {
                    "ticker": "BBB",
                    "analyst_status": "not_requested",
                    "analyst_coverage_pct": 0.0,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stocks.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            out = analyst._load_previous_snapshots(path)

        self.assertEqual(set(out), {"AAA"})
        self.assertEqual(out["AAA"]["eps_next_q"], 1.25)
        self.assertEqual(out["AAA"]["fetched_at"], payload["generated_at"])
        self.assertNotIn("analyst_eps_next_q", out["AAA"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
