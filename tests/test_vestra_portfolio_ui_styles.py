from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class VestraPortfolioUiStyleTests(unittest.TestCase):
    def test_portfolio_ui_keeps_dynamic_kpi_widths_and_moves_static_styles_to_css(self):
        js = read('vestra-portfolio-ui.js')
        css = read('vestra-portfolio-ui.css')
        app_css = read('styles.css')
        self.assertIn("vestra-portfolio-ui.css?v=1.3", js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        self.assertIn('style="width:${x}%"', js)
        self.assertNotIn('x.style.display=', js)
        for token in ('const GROUPS =', 'function ensureHero(', 'data-vpu-tab', 'data-vpu-jump', 'vestra.portfolio.analysisTab'):
            self.assertIn(token, js)
        self.assertIn('.vpu-overview{', css)
        self.assertIn('.vpu-tabs-shell{', css)
        self.assertIn('@media(max-width:620px)', css)
        self.assertIn('@media(min-width:900px)', css)
        self.assertIn('width:min(1280px,calc(100vw - var(--desktop-sidebar-space,var(--desktop-sidebar-w,260px)) - 48px))', css)
        self.assertIn('--desktop-sidebar-space: var(--desktop-sidebar-w)', app_css)
        self.assertIn('body.desktop-sidebar-collapsed { --desktop-sidebar-space: 0px; }', app_css)
        self.assertIn('.vpu-section-card.is-collapsed', css)
        self.assertIn('width:calc(50% - 8px)', css)
        self.assertIn('.vpu-section-card:not(.is-collapsed)', css)
        self.assertIn('width:100%!important', css)
        self.assertIn('function collapseActive(', js)
        self.assertIn('data-vpu-guide="swap"', js)
        self.assertIn('data-vpu-guide="scenario"', js)
        self.assertIn('data-vpu-guide="rebalance"', js)
        self.assertIn('function optimizeTarget(', js)
        self.assertNotIn('uxFocus', js)
        for retired in ('ux455-group-label','ux454-group-label','ux454-nav-title','market-collapse-toolbar','ux-portfolio-shortcuts','ux453-focusbar','ux460-overview','ux461-reveal','v479-portfolio-tabs'):
            self.assertNotIn(retired, js)
        self.assertIn('.vpu-optimize-guide{', css)
        self.assertIn('--desktop-content-max: 1440px', app_css)
        self.assertIn('--desktop-passive-max: 760px', app_css)
        self.assertNotIn('--desktop-content-max: 680px', app_css)

    def test_service_worker_precaches_portfolio_ui_stylesheet(self):
        sw = read('sw.js')
        self.assertIn('"./vestra-portfolio-ui.js"', sw)
        self.assertIn('"./vestra-portfolio-ui.css"', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
