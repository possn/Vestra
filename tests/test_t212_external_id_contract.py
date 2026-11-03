"""Regression contract for Trading 212's official transaction identity.

The source CSV may contain two distinct operations with identical amounts and
timestamps; the broker ID must survive parsing. Historical migrations need
separate coverage before this draft PR can be merged.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Trading212IdentityContract(unittest.TestCase):
    def test_parser_preserves_broker_id_before_generating_event_key(self):
        parser = (ROOT / "app-broker-parsers.js").read_text(encoding="utf-8")
        start = parser.index("function parseBrokerLedgerRows(")
        end = parser.index("function parseBrokerPositionRows(", start)
        body = parser[start:end]
        self.assertRegex(body, r"extId:\s*String\(r\.id\s*\|\|\s*['\"]['\"]\)\.trim\(\)")
        self.assertLess(body.index("extId:"), body.index("evt.key = brokerEventKey(evt)"))

    def test_event_key_prioritizes_scoped_external_id(self):
        core = (ROOT / "app-broker-parsing-core.js").read_text(encoding="utf-8")
        start = core.index("function brokerEventKey(")
        end = core.index("function brokerPositionKey(", start)
        body = core[start:end]
        self.assertIn("brokerExternalIdScope(evt)", body)
        self.assertIn("extId", body)
        self.assertIn("if (extId)", body)


if __name__ == "__main__":
    unittest.main()
