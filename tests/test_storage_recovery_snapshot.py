from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageRecoverySnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app-storage.js').read_text(encoding='utf-8')

    def test_separate_recovery_snapshot_exists(self):
        self.assertIn("const DB_RECOVERY_KEY = 'state_recovery'", self.source)
        self.assertIn("async function storageGetRecovery()", self.source)
        self.assertIn("version: '1.5'", self.source)

    def test_empty_primary_can_recover_from_durable_snapshot(self):
        get_block = self.source.split('async function storageGet(){', 1)[1].split('async function storageSet(raw){', 1)[0]
        self.assertIn("{ source: 'indexeddb-recovery', value: recovery, score: recoveryScore }", get_block)
        self.assertIn("if (primaryScore <= 0)", get_block)
        self.assertIn("return recovered.value", get_block)

    def test_repeated_empty_writes_cannot_degrade_backup(self):
        set_block = self.source.split('async function storageSet(raw){', 1)[1].split('async function storageGetBackup(){', 1)[0]
        self.assertIn("previousScore > 0 && previousScore >= backupScore", set_block)
        self.assertIn("const rescue = richestState", set_block)
        self.assertIn("await idbSet(DB_RECOVERY_KEY, rescue.value)", set_block)

    def test_localstorage_is_mirrored_without_erasing_rich_copy_with_empty_state(self):
        self.assertIn('function localStorageSetSafely(raw, existingValue = null)', self.source)
        self.assertIn('if (rawScore <= 0 && existingScore > 0) return true', self.source)
        set_block = self.source.split('async function storageSet(raw){', 1)[1].split('async function storageGetBackup(){', 1)[0]
        self.assertIn('localStorageSetSafely(raw, localValue)', set_block)

    def test_explicit_clear_removes_all_recovery_copies(self):
        clear_block = self.source.split('async function storageClear(){', 1)[1].split('const api = Object.freeze', 1)[0]
        self.assertIn('await idbDel(DB_KEY)', clear_block)
        self.assertIn('await idbDel(DB_BACKUP_KEY)', clear_block)
        self.assertIn('await idbDel(DB_RECOVERY_KEY)', clear_block)
        self.assertIn('localStorage.removeItem(STORAGE_KEY)', clear_block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
