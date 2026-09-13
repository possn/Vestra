from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeStaticStyleOwnershipTests(unittest.TestCase):
    def test_companion_modules_do_not_inject_runtime_style_elements(self):
        candidates = []
        for path in ROOT.glob('*.js'):
            name = path.name
            if (
                name.startswith(('market-', 'portfolio-', 'vestra-'))
                or name in {'politicians.js', 'mobile-ui-refresh.js', 'dashboard-weekly-events.js', 'dashboard-weekly-events-navigation.js'}
            ):
                candidates.append(path)

        offenders = []
        pattern = re.compile(r"createElement\(\s*['\"]style['\"]\s*\)")
        for path in sorted(candidates):
            source = path.read_text(encoding='utf-8')
            if pattern.search(source):
                offenders.append(path.name)

        self.assertEqual(
            offenders,
            [],
            'Static presentation must live in CSS files, not runtime <style> owners: '
            + ', '.join(offenders),
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
