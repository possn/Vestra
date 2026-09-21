from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StorageResetOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app.js').read_text(encoding='utf-8')

    def test_total_reset_serializes_clear_then_default_state_then_persist_then_render(self):
        block = self.source.split('async function resetAll() {', 1)[1].split('/* ─── SETTINGS', 1)[0]
        self.assertIn('await storageClear();', block)
        self.assertIn('state = safeClone(DEFAULT_STATE);', block)
        self.assertIn('await saveStateAsync();', block)
        self.assertIn('renderAll();', block)
        self.assertLess(block.index('await storageClear();'), block.index('state = safeClone(DEFAULT_STATE);'))
        self.assertLess(block.index('state = safeClone(DEFAULT_STATE);'), block.index('await saveStateAsync();'))
        self.assertLess(block.index('await saveStateAsync();'), block.index('renderAll();'))
        self.assertNotIn('void storageClear();', block)
        self.assertNotIn('saveState();', block)

    def test_total_reset_disables_button_and_does_not_report_success_on_failure(self):
        block = self.source.split('async function resetAll() {', 1)[1].split('/* ─── SETTINGS', 1)[0]
        self.assertIn('if (btn) btn.disabled = true;', block)
        self.assertIn('finally {', block)
        self.assertIn('if (btn) btn.disabled = false;', block)
        self.assertIn('catch (error)', block)
        self.assertIn('toast("Não foi possível apagar todos os dados.", 4000);', block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
