from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Browser companions whose static presentation has been deliberately removed from
# runtime JavaScript. app-ui-core.js is intentionally absent: splash containment is
# a documented critical bootstrap exception and must remain inline to avoid an
# iPhone/PWA cold-start race.
NO_RUNTIME_STYLE_COMPANIONS = (
    'dashboard-weekly-events.js',
    'dashboard-weekly-events-navigation.js',
    'dashboard-ui-refresh.js',
    'mobile-ui-refresh.js',
    'ui-visual-polish.js',
    'market-analysis-tools-runtime.js',
    'market-company-brief.js',
    'market-data-health.js',
    'market-dossier-controls.js',
    'market-ui-polish.js',
    'market-stock-themes-tools.js',
    'market-global-search.js',
    'market-opportunity-lenses.js',
    'market-opportunities.js',
    'portfolio-collapsibles.js',
    'portfolio-sheet-navigation.js',
    'portfolio-card-classifier.js',
    'portfolio-diagnostics.js',
    'vestra-ai-brief.js',
    'vestra-portfolio-ui.js',
    'vestra-portfolio-focus.js',
    'vestra-portfolio-hierarchy.js',
    'vestra-swap-lab.js',
)

# Direct JS -> CSS owners. Some companions intentionally share another owner's
# stylesheet (weekly navigation), while market-ui-polish now has no presentation
# of its own, so neither belongs in this mapping.
DIRECT_STATIC_STYLE_OWNERS = {
    'dashboard-weekly-events.js': 'dashboard-weekly-events.css',
    'dashboard-ui-refresh.js': 'dashboard-ui-refresh.css',
    'mobile-ui-refresh.js': 'mobile-ui-refresh.css',
    'ui-visual-polish.js': 'ui-visual-polish.css',
    'market-analysis-tools-runtime.js': 'market-analysis-tools-runtime.css',
    'market-company-brief.js': 'market-company-brief.css',
    'market-data-health.js': 'market-data-health.css',
    'market-dossier-controls.js': 'market-dossier-controls.css',
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
        for js_name in NO_RUNTIME_STYLE_COMPANIONS:
            js_path = ROOT / js_name
            self.assertTrue(js_path.exists(), js_name)
            source = js_path.read_text(encoding='utf-8')
            if STYLE_CREATION.search(source) or STYLE_TEXT_ASSIGNMENT.search(source):
                offenders.append(js_name)
        self.assertEqual([], offenders)

    def test_direct_style_owners_reference_existing_stylesheets(self):
        for js_name, css_name in DIRECT_STATIC_STYLE_OWNERS.items():
            source = (ROOT / js_name).read_text(encoding='utf-8')
            self.assertTrue((ROOT / css_name).exists(), css_name)
            self.assertIn(css_name, source, f'{js_name} must load {css_name}')

    def test_service_worker_precaches_canonical_static_stylesheets(self):
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        stylesheets = sorted(set(DIRECT_STATIC_STYLE_OWNERS.values()))
        missing = [css for css in stylesheets if f'./{css}' not in sw]
        self.assertEqual([], missing)


if __name__ == '__main__':
    unittest.main(verbosity=2)
