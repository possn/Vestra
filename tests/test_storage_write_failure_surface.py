from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageWriteFailureSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / 'app.js').read_text(encoding='utf-8')
        cls.index = (ROOT / 'index.html').read_text(encoding='utf-8')

    def test_async_save_rejects_false_storage_result(self):
        expected = "async function saveStateAsync() { invalidateRenderCache(); const ok = await storageSet(JSON.stringify(state)); if (!ok) throw new Error('Falha ao guardar o estado local.'); return true; }"
        self.assertIn(expected, self.app)

    def test_reset_success_toast_stays_after_awaited_save(self):
        block = self.app.split('async function resetAll()', 1)[1].split('/* ─── SETTINGS', 1)[0]
        self.assertIn('await saveStateAsync();', block)
        self.assertLess(block.index('await saveStateAsync();'), block.index('toast("Dados apagados.");'))
        self.assertIn('toast("Não foi possível apagar todos os dados.", 4000);', block)

    def test_app_bootstrap_cache_version_bumped_for_persistence_fix(self):
        self.assertIn('app.js?v=20260921v12', self.index)


if __name__ == '__main__':
    unittest.main(verbosity=2)
