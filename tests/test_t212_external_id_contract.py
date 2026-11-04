"""Regression contract for Trading 212's official transaction identity.

The source CSV may contain two distinct operations with identical amounts and
timestamps; the broker ID must survive parsing. Historical migrations need
separate coverage before this draft PR can be merged.
"""
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Trading212IdentityContract(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_migration_function_behaviour(self):
        completed = subprocess.run(
            ["node", "tests/t212-legacy-migration.test.cjs"],
            cwd=ROOT, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_idless_dividends_and_official_id_collision_behaviour(self):
        completed = subprocess.run(
            ["node", "tests/t212-no-id-dividend.test.cjs"],
            cwd=ROOT, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_parser_preserves_broker_id_before_generating_event_key(self):
        parser = (ROOT / "app-broker-parsers.js").read_text(encoding="utf-8")
        start = parser.index("function parseBrokerLedgerRows(")
        end = parser.index("function parseBrokerPositionRows(", start)
        body = parser[start:end]
        self.assertRegex(body, r"extId:\s*String\(r\.id\s*\|\|\s*['\"]['\"]\)\.trim\(\)")
        self.assertLess(body.index("extId:"), body.index("evt.key = brokerEventKey(evt)"))

    def test_legacy_migration_is_scoped_to_matching_t212_fingerprints(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        start = app.index("function migrateLegacyTrading212Events(")
        end = app.index("async function importBrokerFiles(", start)
        migration = app[start:end]
        self.assertIn("brokerEventKey({ ...e, extId: \"\" })", migration)
        self.assertIn("if (String(e.extId || \"\").trim()) return true", migration)
        self.assertIn("fingerprints.has(", migration)
        self.assertIn("trading", migration.lower())
        self.assertEqual(app.count("if (migrateLegacyTrading212Events(bd, evts)) refreshKeySets();"), 2)

    def test_changed_runtimes_are_cache_busted(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        loader = (ROOT / "app-broker-import-loader.js").read_text(encoding="utf-8")
        self.assertIn("rev=20261103-t212-id-migration", html)
        self.assertIn("app-broker-parsers.js?v=20261103-external-id", loader)

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
