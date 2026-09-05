import sys
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

import sec_archive_compat_probe as compat


class FakeResponse:
    def __init__(self, status=200, content_type="text/html"):
        self.status_code = status
        self.headers = {"content-type": content_type, "content-length": "42"}
        self.closed = False

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=25, stream=True):
        self.calls.append({"url": url, "timeout": timeout, "stream": stream})
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class SecArchiveCompatProbeTests(unittest.TestCase):
    def test_probe_matches_normal_streamed_get_and_counts_success(self):
        session = FakeSession([FakeResponse(200), FakeResponse(403), FakeResponse(200, "application/xml")])
        sleeps = []
        report = compat.probe(
            session=session,
            endpoints={"one": "https://sec/1", "two": "https://sec/2", "three": "https://sec/3"},
            sleeper=sleeps.append,
        )
        self.assertEqual(report["request_profile"], "insiders_exact_v1")
        self.assertEqual(report["user_agent"], compat.USER_AGENT)
        self.assertEqual(report["requests"], 3)
        self.assertEqual(report["http_ok"], 2)
        self.assertEqual(sleeps, [0.2, 0.2])
        self.assertTrue(all(call["stream"] for call in session.calls))
        self.assertTrue(all("headers" not in call for call in session.calls))

    def test_exception_is_diagnostic_and_not_raised(self):
        session = FakeSession([RuntimeError("blocked")])
        report = compat.probe(session=session, endpoints={"one": "https://sec/1"}, sleeper=lambda _: None)
        self.assertEqual(report["http_ok"], 0)
        self.assertEqual(report["results"]["one"]["status"], 0)
        self.assertEqual(report["results"]["one"]["error"], "RuntimeError")


if __name__ == "__main__":
    unittest.main(verbosity=2)
