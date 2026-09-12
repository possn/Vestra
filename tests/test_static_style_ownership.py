from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Browser companions whose presentation has been deliberately moved to static CSS.
# app-ui-core.js is intentionally absent: splash containment is a documented critical
# bootstrap exception and must remain inline to avoid a cold-start race on iPhone/PWA.
STATIC_STYLE_COMPANIONS = {
    'dashboard-weekly-events.js': 'dashboard-weekly-events.css',
    'dashboard-weekly-events-navigation.js': 'dashboard-weekly-events-navigation.css',
    'dashboard-ui-refresh.js': 'dashboard-ui-refresh.css',
    'mobile-ui-refresh.js': 'mobile-ui-refresh.css',
    'ui-visual-polish.js': 'ui-visual-polish.css',
    'market-analysis-tools-runtime.js': 'market-analysis-tools-runtime.css',
    'market-company-brief.js': 'market-company-brief.css',
    'market-data-health.js': 'market-data-health.css',
    'market-dossier-controls.js': 'market-dossier-controls.css',
    'market-ui-polish.js': 'market-ui-polish.css',
    'market-stock-themes-tools.js': 'market-stock-themes-tools.css',
    'market-global-search.js': 'market-global-search.css',
    'market-opportunity-lenses.js': 'market-opportunity-lenses.css',
    'market-opportunities.js': 'market-opportunities.css',
    'portfolio-collapsibles.js': 'portfolio-collapsibles.css',
    'portfolio-sheet-navigation.js': 'portfolio-sheet-navigation.css',
    'portfolio-card-classifier.js': 'portfolio-card-classifier.css',
    'portfolio-diagnostics.js': 'portfolio-diagnostics.css',
    'vestra-ai-brief.js': 'vestra-ai-brief.css',
    'vestra-portfolio-ui.js': 'vestra-portfolio-ui.css',
    'vestra-portfolio-focus.js': 'vestra-portfolio-focus.css',
    'vestra-portfolio-hierarchy.js': 'vestra-portfolio-hierarchy.css',
    'vestra-swap-lab.js': 'vestra-swap-lab.css',
}

STYLE_CREATION = re.compile(r"createElement\(\s*['\"]style['\"]\s*\)")
STYLE_TEXT_ASSIGNMENT = re.compile(r"(?:style|styles?|s|x)\.textContent\s*=\s*`", re.IGNORECASE)


class StaticStyleOwnershipTests(unittest.TestCase):
    def test_canonical_companions_do_not_recreate_runtime_style_blocks(self):
        offenders = []
        for js_name, css_name in STATIC_STYLE_COMPANIONS.items():
            js_path = ROOT / js_name
            css_path = ROOT / css_name
            self.assertTrue(js_path.exists(), js_name)
            self.assertTrue(css_path.exists(), css_name)
            source = js_path.read_text(encoding='utf-8')
            self.assertIn(css_name, source, f'{js_name} must load {css_name}')
            if STYLE_CREATION.search(source) or STYLE_TEXT_ASSIGNMENT.search(source):
                offenders.append(js_name)
        self.assertEqual([], offenders)

    def test_service_worker_precaches_canonical_static_stylesheets(self):
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        missing = [css for css in STATIC_STYLE_COMPANIONS.values() if f'./{css}' not in sw]
        self.assertEqual([], missing)


if __name__ == '__main__':
    unittest.main(verbosity=2)
