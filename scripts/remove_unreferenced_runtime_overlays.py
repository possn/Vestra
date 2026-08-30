from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / 'scripts' / 'runtime_js_audit.py'

EXPECTED = [
    'market-enhancements.js',
    'portfolio-navigation-fix.js',
    'vestra-market-close-cleanup-v471.js',
    'vestra-pol-portfolio-v473.js',
    'vestra-politician-activity-v467.js',
    'vestra-politician-filters-v465.js',
    'vestra-politician-ledger-v466.js',
    'vestra-politician-simple-v468.js',
    'vestra-politicians-clean-v475.js',
    'vestra-politicians-dedupe-v463.js',
    'vestra-politicians-flow-v477.js',
    'vestra-politicians-picker-v478.js',
    'vestra-politicians-portfolio-v476.js',
    'vestra-politicians-search-v481.js',
    'vestra-politicians-simple-v472.js',
    'vestra-politicians-unified-v474.js',
    'vestra-portfolio-close-dedupe-v470.js',
    'vestra-portfolio-close-v469.js',
    'vestra-portfolio-overview-v460.js',
    'vestra-portfolio-overview-v461.js',
    'vestra-portfolio-overview-v462.js',
    'vestra-portfolio-tabs-v480.js',
    'vestra-ux-v452.js',
    'vestra-ux-v453.js',
    'vestra-ux-v454.js',
    'vestra-ux-v455.js',
    'vestra-ux-v456.js',
    'vestra-ux-v457.js',
    'vestra-ux-v458.js',
]

spec = importlib.util.spec_from_file_location('runtime_js_audit', AUDIT_PATH)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)

report = audit.build_report()
actual = sorted(report['unreferenced'])
if actual != sorted(EXPECTED):
    raise SystemExit(f'Unreferenced runtime set changed; refusing deletion. actual={actual}')

for name in EXPECTED:
    path = ROOT / name
    if not path.exists():
        raise SystemExit(f'Expected legacy overlay missing before cleanup: {name}')
    path.unlink()

# Strengthen the permanent invariant only after the exact legacy set is removed.
test = ROOT / 'tests' / 'test_runtime_js_reachability.py'
text = test.read_text(encoding='utf-8')
marker = "    def test_audit_never_deletes_unreferenced_scripts(self):\n"
addition = "    def test_no_unreferenced_top_level_runtime_scripts_remain(self):\n        report = audit.build_report()\n        self.assertEqual(report['unreferenced'], [])\n\n"
if 'test_no_unreferenced_top_level_runtime_scripts_remain' not in text:
    if marker not in text:
        raise SystemExit('runtime reachability test anchor missing')
    text = text.replace(marker, addition + marker, 1)
    test.write_text(text, encoding='utf-8')

post = audit.build_report()
if post['unreferenced']:
    raise SystemExit(f'Cleanup left unreferenced scripts: {post["unreferenced"]}')
