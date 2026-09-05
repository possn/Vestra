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
        expected = [
            "AU0000185993: 'IREN'",
            "IE00BLCHJ534: 'PAVE.L'",
            "GB00BL6K5J42: 'EDV.TO'",
            "GB00BVZK7T90: 'UNA.AS'",
            "GB0007188757: 'RIO.L'",
            "CH0334081137: 'CRSP'",
            "US64110L1061: 'NFC.DE'",
            "DE0006047004: 'HEI.DE'",
            "RIO1: 'RIO.L'",
            "'HEI.DE': 'HEI.DE'",
        ]
        for mapping in expected:
            self.assertIn(mapping, text)
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
              GB00BL6K5J42:'EDV.L',
              GB00BVZK7T90:'UNA.L',
              GB0007188757:'RIO1.L',
              CH0334081137:'CRSP.SW'
            }} }};
            window.quoteSanityCheck = () => ({{ok:false, reason:'historical jump'}});
            eval(fs.readFileSync({str(REPAIR)!r}, 'utf8'));

            const map = window.VestraAssetIdentity.ISIN_YAHOO_MAP;
            if (map.AU0000185993 !== 'IREN') process.exit(10);
            if (map.IE00BLCHJ534 !== 'PAVE.L') process.exit(15);
            if (map.GB00BL6K5J42 !== 'EDV.TO') process.exit(17);
            if (map.GB00BVZK7T90 !== 'UNA.AS') process.exit(18);
            if (map.GB0007188757 !== 'RIO.L') process.exit(19);
            if (map.CH0334081137 !== 'CRSP') process.exit(20);
            if (map.US64110L1061 !== 'NFC.DE') process.exit(21);
            if (map.DE0006047004 !== 'HEI.DE') process.exit(22);

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

            const iren = window.quoteSanityCheck(
              {{isin:'AU0000185993', yahooTicker:'IREN'}},
              {{ticker:'IREN', currency:'USD', price:41.65}},
              41.65, 'IREN', 'IREN'
            );
            if (!iren.ok || !iren.canonicalRecovery) process.exit(23);

            const heiWithIsin = window.quoteSanityCheck(
              {{isin:'DE0006047004', ticker:'HEI.DE', yahooTicker:'HEI.DE', currency:'USD'}},
              {{ticker:'HEI.DE', currency:'EUR', price:163.15}},
              163.15, 'HEI.DE', 'HEI.DE'
            );
            if (!heiWithIsin.ok || !heiWithIsin.canonicalRecovery) process.exit(24);

            const heiWithoutIsin = window.quoteSanityCheck(
              {{ticker:'HEI.DE', yahooTicker:'HEI.DE', currency:'USD'}},
              {{ticker:'HEI.DE', currency:'EUR', price:163.15}},
              163.15, 'HEI.DE', 'HEI.DE'
            );
            if (!heiWithoutIsin.ok || !heiWithoutIsin.canonicalRecovery) process.exit(26);

            const rioWithoutIsin = window.quoteSanityCheck(
              {{ticker:'RIO1', yahooTicker:'RIO.L', currency:'USD'}},
              {{ticker:'RIO.L', currency:'GBP', price:52.4}},
              61.2, 'RIO.L', 'RIO.L'
            );
            if (!rioWithoutIsin.ok || !rioWithoutIsin.canonicalRecovery) process.exit(27);

            const wrongHeiCurrency = window.quoteSanityCheck(
              {{ticker:'HEI.DE', yahooTicker:'HEI.DE'}},
              {{ticker:'HEI.DE', currency:'USD', price:163.15}},
              163.15, 'HEI.DE', 'HEI.DE'
            );
            if (wrongHeiCurrency.ok) process.exit(25);

            const other = window.quoteSanityCheck(
              {{isin:'US0378331005', yahooTicker:'AAPL'}},
              {{ticker:'AAPL', currency:'USD', price:200}},
              200, 'AAPL', 'AAPL'
            );
            if (other.ok) process.exit(14);
        """)
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_bootstrap_loads_identity_guard_and_quote_fast_lane(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("loadCanonicalQuoteRepair();", text)
        self.assertIn("quote-canonical-repair.js?v=2.3", text)
        self.assertIn("window.VestraAssetIdentityGuard", text)
        self.assertIn("loadQuoteRefreshPerformance();", text)
        self.assertIn("quote-refresh-performance.js?v=1.0", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
