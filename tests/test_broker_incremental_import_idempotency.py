from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
CORE = (ROOT / "app-broker-parsing-core.js").read_text(encoding="utf-8")


class BrokerIncrementalImportIdempotencyTests(unittest.TestCase):
    def test_trading212_filename_and_external_ids_are_canonical(self):
        self.assertIn('n.includes("t212")', CORE)
        self.assertIn('/^EOF\\d+$/i.test(extId)', CORE)
        self.assertIn('return "TRADING212"', CORE)
        self.assertIn('brokerExternalIdScope(evt)', CORE)

    def test_position_key_does_not_depend_on_report_filename(self):
        start = CORE.index("function brokerPositionKey(pos)")
        end = CORE.index("window.VestraBrokerParsingCore", start)
        block = CORE[start:end]
        self.assertNotIn("sourceName", block)
        self.assertIn("snapshotDate", block)

    def test_updated_reports_replace_covered_older_reports(self):
        self.assertIn("inferBrokerNameFromParsedImport(file.name, parsed)", APP)
        self.assertIn("purgeSupersededBrokerReports", APP)
        self.assertIn("coverage.min <= old.min && coverage.max >= old.max", APP)
        self.assertIn("extendsOld || atLeastAsComplete", APP)

    def test_old_stored_keys_are_recomputed_and_collapsed(self):
        self.assertIn("canonicalizeStoredBrokerKeys(bd)", APP)
        self.assertIn("const key = brokerEventKey(e)", APP)
        self.assertIn("const key = brokerPositionKey(p)", APP)
        rebuild = APP[APP.index("function rebuildBrokerGeneratedData()"):APP.index("function getBrokerImportDiagnostics()")]
        self.assertIn("canonicalizeStoredBrokerKeys(bd);", rebuild)
        self.assertIn("const BROKER_REBUILD_SCHEMA_VERSION = 49;", APP)

    def test_authoritative_snapshot_replaces_same_broker_ledger_position(self):
        rebuild = APP[APP.index("function rebuildBrokerGeneratedData()"):APP.index("function getBrokerImportDiagnostics()")]
        self.assertIn("const authoritativeSnapshotKeys = new Set()", rebuild)
        self.assertIn("coveredByAuthoritativeSnapshot", rebuild)
        self.assertIn('if (coveredByAuthoritativeSnapshot(e)) continue;', rebuild)
        self.assertIn("if (!covered)", rebuild)


if __name__ == "__main__":
    unittest.main(verbosity=2)
