from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = (ROOT / "app-storage.js").read_text(encoding="utf-8")

    def test_richer_legacy_state_recovers_empty_indexeddb(self):
        self.assertIn("function stateRichness(raw)", self.storage)
        self.assertIn("const idbScore = stateRichness(idbValue)", self.storage)
        self.assertIn("const legacyScore = stateRichness(legacyValue)", self.storage)
        self.assertIn("legacyScore > 0 && idbScore <= 0", self.storage)
        self.assertIn("return legacyValue", self.storage)

    def test_failed_read_blocks_background_writes(self):
        self.assertIn("let _readTrusted = true", self.storage)
        self.assertIn("_readTrusted = false", self.storage)
        self.assertIn("if (!_readTrusted)", self.storage)
        self.assertIn("write blocked because the current state followed a failed read", self.storage)
        self.assertIn("if (idbError)", self.storage)
        self.assertIn("throw idbError", self.storage)

    def test_storage_identity_is_unchanged(self):
        self.assertIn("const STORAGE_KEY = 'PF_STATE_V6'", self.storage)
        self.assertIn("const DB_NAME = 'pf_v6'", self.storage)
        self.assertIn("const DB_STORE = 'kv'", self.storage)
        self.assertIn("const DB_KEY = 'state'", self.storage)


if __name__ == "__main__":
    unittest.main(verbosity=2)
