from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import insider_runtime_metrics


class FakeLogger:
    def __init__(self):
        self.rows = []

    def info(self, *args):
        self.rows.append(args)


class FakeModule:
    def __init__(self):
        self.log = FakeLogger()
        self.cached = True

    def _get(self, url, timeout=25):
        if "fail" in url:
            raise RuntimeError("network")
        return {"url": url, "timeout": timeout}

    def _cached_filing(self, cik, filing, ticker):
        return ({"ticker": ticker}, 1, "cache") if self.cached else None

    def annotate(self, tickers, pause=0.0):
        self._get("https://data.sec.gov/submissions/CIK0001.json")
        try:
            self._get("https://data.sec.gov/submissions/CIKfail.json")
        except RuntimeError:
            pass
        self._get("https://www.sec.gov/Archives/edgar/data/1/a.xml")
        self._cached_filing("1", {"accession": "a"}, "AAA")
        self.cached = False
        self._cached_filing("1", {"accession": "b"}, "AAA")
        return {"AAA": {"status": "ok"}}


class InsiderRuntimeMetricsTests(unittest.TestCase):
    def test_observability_counts_transport_without_changing_result(self):
        module = FakeModule()
        clock_values = iter([10.0, 12.5])
        metrics = insider_runtime_metrics.install(module=module, clock=lambda: next(clock_values))
        result = module.annotate(["AAA"])
        self.assertEqual(result, {"AAA": {"status": "ok"}})
        self.assertEqual(metrics["submissions_requests"], 2)
        self.assertEqual(metrics["submissions_failures"], 1)
        self.assertEqual(metrics["archive_requests"], 1)
        self.assertEqual(metrics["archive_failures"], 0)
        self.assertEqual(metrics["cache_hits"], 1)
        self.assertEqual(metrics["cache_misses"], 1)
        self.assertTrue(module.log.rows)
        self.assertIn("Insider transport summary", module.log.rows[-1][0])

    def test_install_is_idempotent(self):
        module = FakeModule()
        first = insider_runtime_metrics.install(module=module)
        wrapped = module.annotate
        second = insider_runtime_metrics.install(module=module)
        self.assertIs(first, second)
        self.assertIs(wrapped, module.annotate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
