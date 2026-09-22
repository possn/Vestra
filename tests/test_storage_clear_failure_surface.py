from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STORAGE = (ROOT / "app-storage.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class StorageClearFailureSurfaceTests(unittest.TestCase):
    def test_clear_checks_all_indexeddb_deletes(self):
        block = STORAGE.split("async function storageClear()", 1)[1].split("const api = Object.freeze", 1)[0]
        self.assertIn("for (const key of [DB_KEY, DB_BACKUP_KEY, DB_RECOVERY_KEY, DB_EMPTY_AUTH_KEY])", block)
        self.assertIn("deleted = await idbDel(key)", block)
        self.assertIn("if (!deleted) idbCleared = false;", block)

    def test_clear_only_fails_when_both_backends_fail(self):
        block = STORAGE.split("async function storageClear()", 1)[1].split("const api = Object.freeze", 1)[0]
        self.assertIn("if (!idbCleared && !localCleared)", block)
        self.assertIn("throw idbFailure('Persistent state clear failed');", block)
        self.assertIn("cleared-local-fallback", block)

    def test_localstorage_clear_failure_is_tracked(self):
        block = STORAGE.split("async function storageClear()", 1)[1].split("const api = Object.freeze", 1)[0]
        self.assertIn("localCleared = false;", block)

    def test_authoritative_local_empty_precedes_stale_indexeddb_primary(self):
        block = STORAGE.split("async function storageGet()", 1)[1].split("async function storageSet", 1)[0]
        local = block.index("const authoritativeEmptyLocal")
        local_return = block.index("return localValue;", local)
        primary_return = block.index("if (primary) {")
        self.assertLess(local, primary_return)
        self.assertLess(local_return, primary_return)

    def test_storage_runtime_rolls_forward(self):
        self.assertIn("Vestra persistence layer v1.7", STORAGE)
        self.assertIn("version: '1.7'", STORAGE)
        self.assertIn("app-storage.js?v=1.7", INDEX)


if __name__ == "__main__":
    unittest.main(verbosity=2)
