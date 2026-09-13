from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CanonicalDossierNavigationOwnershipTests(unittest.TestCase):
    def test_companions_do_not_bypass_canonical_dossier_navigation(self):
        # These files are the intentional navigation/render owners or documented
        # special cases. Other companions should express ticker intent via
        # data-market-ticker or VestraNavigation.openCompany().
        allowed = {
            'market.js',
            'portfolio-sheet-navigation.js',
            'market-data-loader.js',
            'market-global-search.js',  # remote-live lookup outside the catalog
        }
        patterns = {
            'VestraMarket.openTicker': re.compile(r'VestraMarket\s*\?*\.\s*openTicker'),
            'VestraMarketData.openDossier': re.compile(r'VestraMarketData\s*\?*\.\s*openDossier'),
            'direct market view switch': re.compile(r"\bsetView\(\s*['\"]market['\"]\s*\)"),
        }

        offenders = []
        for path in sorted(ROOT.glob('*.js')):
            name = path.name
            if name in allowed:
                continue
            if not (
                name.startswith(('market-', 'portfolio-', 'vestra-'))
                or name in {
                    'politicians.js',
                    'mobile-ui-refresh.js',
                    'dashboard-weekly-events.js',
                    'dashboard-weekly-events-navigation.js',
                }
            ):
                continue
            source = path.read_text(encoding='utf-8')
            for label, pattern in patterns.items():
                if pattern.search(source):
                    offenders.append(f'{name}: {label}')

        self.assertEqual(
            offenders,
            [],
            'Normal dossier navigation must go through the canonical owner: '
            + '; '.join(offenders),
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
