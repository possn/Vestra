import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = types.ModuleType("yfinance")

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    adapters_stub = types.ModuleType("requests.adapters")
    adapters_stub.HTTPAdapter = object
    sys.modules["requests"] = requests_stub
    sys.modules["requests.adapters"] = adapters_stub

if "urllib3" not in sys.modules:
    urllib3_stub = types.ModuleType("urllib3")
    util_stub = types.ModuleType("urllib3.util")
    retry_stub = types.ModuleType("urllib3.util.retry")

    class Retry:
        def __init__(self, *args, **kwargs):
            pass

    retry_stub.Retry = Retry
    sys.modules["urllib3"] = urllib3_stub
    sys.modules["urllib3.util"] = util_stub
    sys.modules["urllib3.util.retry"] = retry_stub

from fundamentals import RawMetrics
import sec_archives_runtime as runtime


class _InnerClient:
    def __init__(self):
        self.requests = 0
        self.text_calls = []
        self.content_calls = []

    def text(self, url, timeout=25):
        self.requests += 1
        self.text_calls.append(url)
        return f"text:{url}"

    def content(self, url, timeout=25):
        self.requests += 1
        self.content_calls.append(url)
        return b"content"


class SecArchivesBudgetRuntimeTests(unittest.TestCase):
    def test_filingless_rows_do_not_reduce_filing_backed_budget(self):
        rows = [
            RawMetrics(ticker="AAA", quote_type="EQUITY"),
            RawMetrics(ticker="BBB", quote_type="EQUITY"),
            RawMetrics(ticker="CCC", quote_type="EQUITY"),
        ]
        cmap = {"AAA": 1, "BBB": 2, "CCC": 3}
        filings = {2: {"accession": "b"}, 3: {"accession": "c"}}

        # AAA has no filing. To obtain one filing-backed non-priority candidate,
        # the underlying legacy counter must be allowed to scan two raw rows.
        cap = runtime._effective_nonpriority_cap(rows, cmap, filings, requested=1)
        self.assertEqual(cap, 2)

        # Reaching two filing-backed candidates requires all three rows, but no
        # additional filing-backed work beyond the requested two is introduced.
        cap = runtime._effective_nonpriority_cap(rows, cmap, filings, requested=2)
        self.assertEqual(cap, 3)

    def test_priority_rows_are_exempt_from_nonpriority_budget(self):
        rows = [
            RawMetrics(ticker="AAA", quote_type="EQUITY"),
            RawMetrics(ticker="BBB", quote_type="EQUITY"),
        ]
        cmap = {"AAA": 1, "BBB": 2}
        filings = {1: {"accession": "a"}, 2: {"accession": "b"}}
        cap = runtime._effective_nonpriority_cap(rows, cmap, filings, requested=1, priority={"AAA"})
        self.assertEqual(cap, 1)

    def test_master_index_text_is_replayed_without_second_request(self):
        inner = _InnerClient()
        client = runtime._ReplayArchiveClient(inner)
        self.assertEqual(client.text("master"), "text:master")
        self.assertEqual(client.text("master"), "text:master")
        self.assertEqual(inner.text_calls, ["master"])
        self.assertEqual(client.requests, 1)

        self.assertEqual(client.content("instance"), b"content")
        self.assertEqual(client.requests, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
