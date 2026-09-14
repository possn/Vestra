from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class DossierObserverPipelineTests(unittest.TestCase):
    def test_company_brief_owns_shared_sheet_scoped_dossier_normalizer_observer(self):
        company = read('market-company-brief.js')
        metric = read('market-metric-cleanup.js')
        controls = read('market-dossier-controls.js')
        self.assertEqual(company.count('new MutationObserver'), 1)
        self.assertEqual(metric.count('new MutationObserver'), 0)
        self.assertEqual(controls.count('new MutationObserver'), 0)
        self.assertIn("const sh=document.getElementById('marketSheet');if(!sh)return", company)
        self.assertIn("mo.observe(sh,{childList:true,subtree:true})", company)
        self.assertNotIn("mo.observe(document.body,{childList:true,subtree:true})", company)
        self.assertIn('window.VestraMarketMetricCleanup?.refresh?.()', company)
        self.assertIn('window.VestraMarketDossierControls?.normalizeButtons?.()', company)
        self.assertIn('refresh:refreshDossier', company)

    def test_normalizers_keep_explicit_refresh_contracts(self):
        metric = read('market-metric-cleanup.js')
        controls = read('market-dossier-controls.js')
        company = read('market-company-brief.js')
        self.assertIn("version:'1.2'", metric)
        self.assertIn("version: '1.6'", controls)
        self.assertIn("version:'2.1'", company)
        self.assertIn('refresh:repair', metric)
        self.assertIn('normalizeButtons,', controls)
        self.assertIn("market-dossier-controls.js?v=1.6", company)

    def test_ai_brief_keeps_separate_sheet_scoped_dossier_lifecycle(self):
        ai = read('vestra-ai-brief.js')
        self.assertEqual(ai.count('new MutationObserver'), 1)
        self.assertIn("if(!sh||sh.hidden||!t(sh.dataset.ticker)||!host)return", ai)
        self.assertIn("const sh=document.getElementById('marketSheet');if(!sh)return", ai)
        self.assertIn(".observe(sh,{childList:true,subtree:true})", ai)
        self.assertNotIn(".observe(document.body,{childList:true,subtree:true})", ai)
        self.assertIn('install()', ai)


if __name__ == '__main__':
    unittest.main(verbosity=2)
