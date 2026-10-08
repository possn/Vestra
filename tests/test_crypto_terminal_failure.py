"""Crypto loader terminal failure behavior prevents repeated implicit retries."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CryptoTerminalStateTests(unittest.TestCase):
    def test_failed_request_marks_attempt_complete(self):
        js=(ROOT/'market.js').read_text()
        start=js.index('async function loadCryptoMarket()')
        end=js.index('function renderCrypto()',start)
        loader=js[start:end]
        self.assertIn("M.cryptoError=err?.message||'Falha ao carregar crypto'",loader)
        self.assertIn("M.cryptoLoaded=true;\n        return [];",loader)
        self.assertIn("if(M.cryptoLoaded)return M.cryptoRows;",loader)
        self.assertIn("if(M.cryptoError&&!M.cryptoRows.length)",js[end:])
if __name__=='__main__': unittest.main()
