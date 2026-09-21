from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageEmptyAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app-storage.js').read_text(encoding='utf-8')

    def test_trusted_empty_state_gets_explicit_authority_marker(self):
        set_block = self.source.split('async function storageSet(raw){', 1)[1].split('async function storageGetBackup(){', 1)[0]
        self.assertIn("const authoritativeEmpty = rawScore === 0 && validState(raw) && _stateReadAttempted && _stateReadTrusted", set_block)
        self.assertIn("await idbSet(DB_EMPTY_AUTH_KEY, raw)", set_block)
        self.assertIn("localStorageSetSafely(raw, localValue, authoritativeEmpty)", set_block)

    def test_authoritative_empty_primary_wins_over_richer_recovery_snapshot(self):
        get_block = self.source.split('async function storageGet(){', 1)[1].split('async function storageSet(raw){', 1)[0]
        self.assertIn("const authoritativeEmptyPrimary = primaryScore === 0 && validState(primary) && emptyAuthority === primary", get_block)
        self.assertIn("markStateReadTrusted('indexeddb-empty-authoritative')", get_block)
        self.assertLess(get_block.index("authoritativeEmptyPrimary"), get_block.index("const recovered = richestState(["))

    def test_unacknowledged_empty_primary_still_allows_recovery(self):
        get_block = self.source.split('async function storageGet(){', 1)[1].split('async function storageSet(raw){', 1)[0]
        self.assertIn("if (primaryScore <= 0)", get_block)
        self.assertIn("{ source: 'indexeddb-recovery', value: recovery, score: recoveryScore }", get_block)

    def test_empty_authority_is_content_bound_and_removed_on_nonempty_write_or_clear(self):
        self.assertIn("emptyAuthority === primary", self.source)
        self.assertIn("localEmptyAuthority === localValue", self.source)
        set_block = self.source.split('async function storageSet(raw){', 1)[1].split('async function storageGetBackup(){', 1)[0]
        self.assertIn("await idbDel(DB_EMPTY_AUTH_KEY)", set_block)
        clear_block = self.source.split('async function storageClear(){', 1)[1].split('const api = Object.freeze', 1)[0]
        self.assertIn("await idbDel(DB_EMPTY_AUTH_KEY)", clear_block)
        self.assertIn("localStorage.removeItem(EMPTY_AUTH_STORAGE_KEY)", clear_block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
