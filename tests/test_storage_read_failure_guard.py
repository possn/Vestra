from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageReadFailureGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app-storage.js').read_text(encoding='utf-8')

    def test_failed_primary_read_blocks_state_writes_without_valid_fallback(self):
        self.assertIn("let _stateReadAttempted = false", self.source)
        self.assertIn("let _stateReadTrusted = false", self.source)
        self.assertIn("function blockStateWrites(error)", self.source)
        self.assertIn("blockStateWrites(idbError)", self.source)
        self.assertIn("if (_stateReadAttempted && !_stateReadTrusted)", self.source)
        self.assertIn("State write blocked because the current session had a failed state read", self.source)
        self.assertIn("return false", self.source)

    def test_direct_write_before_any_read_keeps_existing_storage_api_contract(self):
        self.assertIn("writeBlocked: _stateReadAttempted && !_stateReadTrusted", self.source)
        self.assertNotIn("if (!_stateReadTrusted)", self.source)

    def test_successful_empty_read_is_still_trusted_for_first_run(self):
        primary = self.source.split('async function storageGet(){', 1)[1].split('async function storageSet(raw){', 1)[0]
        self.assertIn("markStateReadTrusted('empty')", primary)
        self.assertIn("return null", primary)

    def test_preserved_state_is_considered_only_when_primary_is_empty(self):
        self.assertIn("function stateRichness(raw)", self.source)
        self.assertIn("function richestState(candidates)", self.source)
        self.assertIn("const primaryScore = stateRichness(primary)", self.source)
        self.assertIn("const backupScore = stateRichness(backup)", self.source)
        self.assertIn("const recoveryScore = stateRichness(recovery)", self.source)
        self.assertIn("const localScore = stateRichness(localValue)", self.source)
        recovery = self.source.split("if (primaryScore <= 0)", 1)[1].split("if (primary)", 1)[0]
        self.assertIn("const recovered = richestState([", recovery)
        self.assertIn("{ source: 'indexeddb-recovery', value: recovery, score: recoveryScore }", recovery)
        self.assertIn("{ source: 'indexeddb-backup', value: backup, score: backupScore }", recovery)
        self.assertIn("{ source: 'localstorage', value: localValue, score: localScore }", recovery)
        self.assertIn("markStateReadTrusted(recovered.source)", recovery)
        self.assertIn("return recovered.value", recovery)
        self.assertIn(".sort((a, b) => b.score - a.score)", self.source)

    def test_valid_nonempty_primary_remains_authoritative(self):
        recovery = self.source.split("if (primaryScore <= 0)", 1)[1].split("if (primary)", 1)[0]
        self.assertIn("const recovered = richestState([", recovery)
        after_recovery = self.source.split("if (primaryScore <= 0)", 1)[1]
        self.assertIn("if (primary)", after_recovery)
        self.assertIn("markStateReadTrusted('indexeddb')", after_recovery)
        self.assertNotIn("backupScore > primaryScore", self.source)
        self.assertNotIn("localScore > primaryScore", self.source)
        self.assertNotIn("recoveryScore > primaryScore", self.source)

    def test_previous_indexeddb_state_is_saved_as_recovery_backup_before_replace(self):
        self.assertIn("const DB_BACKUP_KEY = 'state_backup'", self.source)
        self.assertIn("await idbSet(DB_BACKUP_KEY, previous)", self.source)
        self.assertIn("async function storageGetBackup()", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
