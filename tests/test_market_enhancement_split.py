from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class MarketEnhancementSplitTests(unittest.TestCase):
    def test_hotfix_uses_canonical_modules_not_legacy_overlays(self):
        h = read('index.html')
        self.assertNotIn('market-hotfix.js', h)
        self.assertNotIn('market-enhancements.js', h)
        self.assertNotIn('vestra-ux-v452.js', h)
        for module in (
            'market-company-brief.js?v=1.0',
            'market-metric-cleanup.js?v=1.0',
            'portfolio-collapsibles.js?v=1.2',
            'portfolio-card-classifier.js?v=1.2',
            'portfolio-diagnostics.js?v=1.0',
            'vestra-ai-brief.js?v=1.0',
            'portfolio-dossier-routing.js?v=1.0',
        ):
            self.assertIn(module, h)

    def test_company_brief_reuses_market_runtime_and_keeps_copy_fallbacks(self):
        s = read('market-company-brief.js')
        self.assertIn('window.VestraMarket', s)
        self.assertIn('resolvePortfolioStock', s)
        self.assertNotIn("fetch('./data/stocks-index.json'", s)
        self.assertNotIn("fetch('./data/stocks.json'", s)
        for token in ('business_summary', 'longBusinessSummary', 'company_description', 'Empresa cotada acompanhada pelo universo Vestra.'):
            self.assertIn(token, s)
        self.assertIn('new MutationObserver', s)
        self.assertIn('requestAnimationFrame', s)
        self.assertIn('window.VestraMarketCompanyBrief', s)

    def test_metric_cleanup_preserves_invalid_multiple_rules(self):
        s = read('market-metric-cleanup.js')
        for label in ("'P/E'", "'Forward P/E'", "'EV/EBITDA'", "'PEG'"):
            self.assertIn(label, s)
        self.assertIn("if(x!=null&&x<=0)v.textContent='—'", s)
        self.assertIn('window.VestraMarketMetricCleanup', s)

    def test_collapsibles_preserve_storage_and_controls(self):
        s = read('portfolio-collapsibles.js')
        self.assertIn("const COLLAPSE_KEY='vestra-market-collapse-v1'", s)
        for token in ('data-collapse-toggle', 'data-collapse-all', 'Abrir tudo', 'Fechar tudo', 'market-collapse-toolbar'):
            self.assertIn(token, s)
        self.assertIn('window.VestraPortfolioCollapsibles', s)

    def test_classifier_preserves_all_portfolio_kinds_shortcuts_and_hints(self):
        s = read('portfolio-card-classifier.js')
        for kind in ('research','priority','map','reinforce','review','overlap','swap','scenario','target','history','risk','stress'):
            self.assertIn(f"kind:'{kind}'", s)
        for token in ('data-ux-jump="priority"','data-ux-jump="swap"','data-ux-jump="overlap"','data-ux-jump="risk"'):
            self.assertIn(token, s)
        self.assertIn('Trocas inteligentes · compara alternativas sem assumir que vender é obrigatório.', s)
        self.assertIn('Sobreposição · mostra onde várias posições estão a comprar a mesma exposição.', s)
        self.assertIn('window.VestraPortfolioCardClassifier', s)

    def test_service_worker_caches_all_canonical_modules(self):
        sw = read('sw.js')
        self.assertIn('Vestra Service Worker v10.13', sw)
        self.assertIn('vestra-cache-v127', sw)
        self.assertIn('staleWhileRevalidate', sw)
        for module in ('./market-live-overlay.js', './market-company-brief.js', './market-metric-cleanup.js', './portfolio-collapsibles.js', './portfolio-card-classifier.js', './portfolio-diagnostics.js', './vestra-ai-brief.js', './portfolio-dossier-routing.js'):
            self.assertIn(module, sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
