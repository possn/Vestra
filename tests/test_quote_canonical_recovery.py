from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPAIR = ROOT / "quote-canonical-repair.js"
BOOTSTRAP = ROOT / "market-company-brief.js"
IDENTITY = ROOT / "app-asset-identity.js"


class CanonicalQuoteRecoveryTests(unittest.TestCase):
    def test_runtime_module_is_valid_javascript(self):
        subprocess.run(["node", "--check", str(REPAIR)], check=True, cwd=ROOT)
        subprocess.run(["node", "--check", str(BOOTSTRAP)], check=True, cwd=ROOT)

    def test_siemens_healthineers_has_authoritative_isin_mapping(self):
        text = IDENTITY.read_text(encoding="utf-8")
        self.assertIn('"DE000SHL1006":"SHL.DE"', text)

    def test_runtime_repairs_ambiguous_broker_listing_maps(self):
        text = REPAIR.read_text(encoding="utf-8")
        self.assertIn("AU0000185993: 'IREN'", text)
        self.assertIn("IE00BLCHJ534: 'PAVE.L'", text)
        self.assertIn("GB00BL6K5J42: 'EDV.TO'", text)
        self.assertIn("applyIdentityMapRepairs();", text)

    def test_recovery_is_narrow_and_runtime_effective(self):
        script = textwrap.dedent(f"""
            const fs = require('fs');
            global.window = global;
            global.document = {{ addEventListener: () => {{}} }};
            window.VestraAssetIdentity = {{ ISIN_YAHOO_MAP: {{
              DE000SHL1006:'SHL.DE',
              US0378331005:'AAPL',
              US12468P1049:'AI',
              AU0000185993:'IREN.AX',
              IE00BLCHJ534:'PAVE.DE',
              GB00BL6K5J42:'EDV.L'
            }} }};
            window.quoteSanityCheck = () => ({{ok:false, reason:'historical jump'}});
            eval(fs.readFileSync({str(REPAIR)!r}, 'utf8'));

            if (window.VestraAssetIdentity.ISIN_YAHOO_MAP.AU0000185993 !== 'IREN') process.exit(10);
            if (window.VestraAssetIdentity.ISIN_YAHOO_MAP.IE00BLCHJ534 !== 'PAVE.L') process.exit(15);
            if (window.VestraAssetIdentity.ISIN_YAHOO_MAP.GB00BL6K5J42 !== 'EDV.TO') process.exit(17);

            const good = window.quoteSanityCheck(
              {{isin:'DE000SHL1006'}},
              {{ticker:'SHL.DE', currency:'EUR', price:34.2}},
              34.2, 'SHL.DE', 'SHL.DE'
            );
            if (!good.ok || !good.canonicalRecovery) process.exit(11);

            const usd = window.quoteSanityCheck(
              {{isin:'DE000SHL1006'}},
              {{ticker:'SHL.DE', currency:'USD', price:34.2}},
              34.2, 'SHL.DE', 'SHL.DE'
            );
            if (usd.ok) process.exit(12);

            const absurd = window.quoteSanityCheck(
              {{isin:'DE000SHL1006'}},
              {{ticker:'SHL.DE', currency:'EUR', price:78224.14}},
              78224.14, 'SHL.DE', 'SHL.DE'
            );
            if (absurd.ok) process.exit(13);

            const c3 = window.quoteSanityCheck(
              {{isin:'US12468P1049', yahooTicker:'AI'}},
              {{ticker:'AI', currency:'USD', price:12.5}},
              12.5, 'AI', 'AI'
            );
            if (!c3.ok || !c3.canonicalRecovery) process.exit(16);

            const other = window.quoteSanityCheck(
              {{isin:'US0378331005', yahooTicker:'AAPL'}},
              {{ticker:'AAPL', currency:'USD', price:200}},
              200, 'AAPL', 'AAPL'
            );
            if (other.ok) process.exit(14);
        """)
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_bootstrap_loads_identity_guard_before_user_interaction(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("loadCanonicalQuoteRepair();", text)
        self.assertIn("quote-canonical-repair.js?v=2.1", text)
        self.assertIn("window.VestraAssetIdentityGuard", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
