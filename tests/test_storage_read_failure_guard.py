from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageReadFailureGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app-storage.js').read_text(encoding='utf-8')

    def test_failed_primary_read_blocks_state_writes_without_valid_fallback(self):
        self.assertIn("let _stateReadTrusted = false", self.source)
        self.assertIn("function blockStateWrites(error)", self.source)
        self.assertIn("blockStateWrites(error)", self.source)
        self.assertIn("if (!_stateReadTrusted)", self.source)
        self.assertIn("State write blocked because the current session did not complete a trusted state read", self.source)
        self.assertIn("return false", self.source)

    def test_successful_empty_read_is_still_trusted_for_first_run(self):
        primary = self.source.split('async function storageGet(){', 1)[1].split('async function storageSet(raw){', 1)[0]
        self.assertIn("const value = await idbGet(DB_KEY)", primary)
        self.assertIn("markStateReadTrusted()", primary)
        self.assertIn("return null", primary)

    def test_valid_local_storage_fallback_unlocks_writes(self):
        self.assertIn("if (fallback.ok && fallback.value)", self.source)
        self.assertIn("markStateReadTrusted();\n          return fallback.value", self.source)

    def test_previous_indexeddb_state_is_saved_as_recovery_backup_before_replace(self):
        self.assertIn("const DB_BACKUP_KEY = 'state_backup'", self.source)
        self.assertIn("await idbSet(DB_BACKUP_KEY, previous)", self.source)
        self.assertIn("async function storageGetBackup()", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
