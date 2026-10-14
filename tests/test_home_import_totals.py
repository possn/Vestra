from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.js').read_text(encoding='utf-8')
HOME=(ROOT/'vestra-intelligence-home.js').read_text(encoding='utf-8')

class HomeImportTotalsTests(unittest.TestCase):
    def test_read_only_snapshot_uses_canonical_totals_and_hydration_gate(self):
        self.assertIn('window.VestraFinancialTotals = () => {',APP)
        self.assertIn('window.__vestraAppHydrated !== true',APP)
        self.assertIn('const t=calcTotals();',APP)
        self.assertIn('net:t.net, assetsTotal:t.assetsTotal, liabsTotal:t.liabsTotal',APP)

    def test_import_updates_home_from_canonical_portfolio(self):
        imp=APP.split('async function importJSON(file)',1)[1].split('async function resetAll()',1)[0]
        self.assertIn('renderAll();',imp)
        self.assertIn("vestra:portfolio-totals-updated",imp)
        self.assertIn("window.VestraFinancialTotals?.()",HOME)
        self.assertIn("window.addEventListener('vestra:portfolio-totals-updated'",HOME)
        self.assertNotIn("value.textContent = originalValue",HOME)

    def test_privacy_still_masks_before_snapshot(self):
        hero=HOME.split('function syncWealthHero(host)',1)[1].split('function init()',1)[0]
        self.assertLess(hero.index('if (concealed) {'),hero.index('const totals = window.VestraFinancialTotals?.();'))
        self.assertIn("value.textContent = '••• €'",hero)

if __name__=='__main__':unittest.main()
