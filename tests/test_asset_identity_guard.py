from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "quote-canonical-repair.js"


class AssetIdentityGuardTests(unittest.TestCase):
    def run_node(self, assertions: str):
        module_path = str(MODULE).replace('\\', '\\\\')
        script = textwrap.dedent(f"""
            const fs = require('fs');
            global.window = {{
              VestraAssetIdentity: {{
                ISIN_YAHOO_MAP: {{
                  DE000SHL1006: 'SHL.DE',
                  PTCOR0AE0006: 'COR.LS',
                  US7561091049: 'O'
                }}
              }},
              quoteSanityCheck: () => ({{ok:false, reason:'jump'}})
            }};
            global.document = {{ addEventListener: () => {{}} }};
            eval(fs.readFileSync('{module_path}', 'utf8'));
            {assertions}
        """)
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_module_syntax(self):
        subprocess.run(["node", "--check", str(MODULE)], cwd=ROOT, check=True)

    def test_detects_canonical_stored_ticker_mismatch(self):
        self.run_node("""
            const g = window.VestraAssetIdentityGuard;
            const a = g.assess({isin:'DE000SHL1006', yahooTicker:'SHL'});
            if (a.canonicalTicker !== 'SHL.DE') process.exit(11);
            if (!a.issues.some(x => x.code === 'stored_ticker_mismatch')) process.exit(12);
        """)

    def test_generic_recovery_requires_exact_canonical_identity(self):
        self.run_node("""
            const g = window.VestraAssetIdentityGuard;
            const asset = {isin:'PTCOR0AE0006', yahooTicker:'COR'};
            if (!g.canonicalRecoveryAllowed(asset, {ticker:'COR.LS', currency:'EUR', price:8.5}, 'COR.LS', 'COR')) process.exit(21);
            if (g.canonicalRecoveryAllowed(asset, {ticker:'COR', currency:'USD', price:270}, 'COR', 'COR')) process.exit(22);
            if (g.canonicalRecoveryAllowed(asset, {ticker:'COR.LS', currency:'USD', price:8.5}, 'COR.LS', 'COR')) process.exit(23);
        """)

    def test_does_not_bypass_normal_sanity_when_identity_was_already_canonical(self):
        self.run_node("""
            const g = window.VestraAssetIdentityGuard;
            const asset = {isin:'PTCOR0AE0006', yahooTicker:'COR.LS'};
            if (g.canonicalRecoveryAllowed(asset, {ticker:'COR.LS', currency:'EUR', price:8.5}, 'COR.LS', 'COR.LS')) process.exit(31);
        """)

    def test_siemens_known_corruption_can_still_be_recovered(self):
        self.run_node("""
            const g = window.VestraAssetIdentityGuard;
            const asset = {isin:'DE000SHL1006', yahooTicker:'SHL.DE'};
            if (!g.canonicalRecoveryAllowed(asset, {ticker:'SHL.DE', currency:'EUR', price:44.2}, 'SHL.DE', 'SHL.DE')) process.exit(41);
            if (g.canonicalRecoveryAllowed(asset, {ticker:'SHL.DE', currency:'USD', price:44.2}, 'SHL.DE', 'SHL.DE')) process.exit(42);
            if (g.canonicalRecoveryAllowed(asset, {ticker:'SHL.DE', currency:'EUR', price:78224}, 'SHL.DE', 'SHL.DE')) process.exit(43);
        """)

    def test_audit_assets_reports_summary_without_mutating(self):
        self.run_node("""
            const g = window.VestraAssetIdentityGuard;
            const assets = [
              {id:'a', isin:'DE000SHL1006', yahooTicker:'SHL'},
              {id:'b', isin:'US7561091049', yahooTicker:'O'}
            ];
            const before = JSON.stringify(assets);
            const report = g.auditAssets(assets);
            if (report.total !== 2 || report.flagged !== 1) process.exit(51);
            if (JSON.stringify(assets) !== before) process.exit(52);
        """)


if __name__ == "__main__":
    unittest.main(verbosity=2)
