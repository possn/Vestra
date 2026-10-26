#!/usr/bin/env python3
"""Synthetic transport mocks only, no historical outcomes."""
import io
import unittest
from provider_access_probe import probe_eodhd

class FakeResponse:
    def __init__(self, payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.payload

class ProbeTests(unittest.TestCase):
    def test_missing_token_is_blocked(self):
        self.assertEqual(probe_eodhd(token="", symbol="AAPL.US",
                         transport=lambda *a, **kw: None)["status"],"BLOCKED_DATA_ACCESS")

    def test_demo_cannot_validate_other_symbols(self):
        self.assertEqual(probe_eodhd(token="demo",symbol="ZZZZ.US")["status"],
                         "BLOCKED_DEMO_SCOPE")

    def test_demo_never_certifies_alpha(self):
        seen=[]
        def transport(request,timeout):
            seen.append(request.full_url)
            return FakeResponse(b'[{"date":"2020-01-02","open":100}]')
        result=probe_eodhd(token="demo",transport=transport)
        self.assertEqual(result["status"],"DEMO_CONNECTIVITY_ONLY")
        self.assertFalse(result["empirical_validated"])
        self.assertNotIn("demo",str(result))

    def test_bad_payload_rejected(self):
        result=probe_eodhd(token="demo",
                           transport=lambda *args,**kw:FakeResponse(b'{}'))
        self.assertEqual(result["status"],"REJECTED_PROVIDER_RESPONSE")

    def test_private_token_not_echoed(self):
        key="DO_NOT_ECHO_TEST_SECRET"
        result=probe_eodhd(token=key,
                           transport=lambda *args,**kw:FakeResponse(
                               b'[{"date":"2020-01-02"}]'))
        self.assertNotIn(key,str(result))
        self.assertFalse(result["empirical_validated"])

if __name__=="__main__":
    unittest.main()
