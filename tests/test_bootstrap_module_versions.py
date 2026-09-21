from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapModuleVersionTests(unittest.TestCase):
    def test_storage_loader_version_matches_declared_persistence_version(self):
        storage = (ROOT / 'app-storage.js').read_text(encoding='utf-8')
        index = (ROOT / 'index.html').read_text(encoding='utf-8')

        declared = re.search(r'Vestra persistence layer v([0-9.]+)', storage)
        loaded = re.search(r'app-storage\.js\?v=([0-9.]+)', index)

        self.assertIsNotNone(declared, 'app-storage.js must declare its persistence version')
        self.assertIsNotNone(loaded, 'index.html must cache-bust app-storage.js')
        self.assertEqual(
            loaded.group(1),
            declared.group(1),
            'index.html must load the same app-storage.js version declared by the persistence module',
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
