from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')

class QuoteUiDividendRepairTests(unittest.TestCase):
  def test_canonical_quote_identities(self):
    core=read('app-broker-parsing-core.js'); ident=read('app-asset-identity.js')
    self.assertIn('"AT0000A3EPA4|AMS": "AMS.SW"',core)
    self.assertIn('return "EDV.TO"',core)
    self.assertIn('return "NEO.TO"',core)
    self.assertIn('return "MPT"',core)
    self.assertIn('"US58463J3041":"MPT"',ident)
    self.assertIn('"CA64046G1063":"NEO.TO"',ident)
  def test_sanity_resets_only_on_identity_change(self):
    a=read('app.js')
    self.assertIn('const authoritativeLegacyRepair = !!(',a)
    self.assertIn('(identityChanged || authoritativeLegacyRepair) ? 0 :',a)
    self.assertIn('_previousYahooTicker',a)
    self.assertIn('asset.yahooTicker = _resolvedYahoo',a)
    self.assertIn('"OD7F.DE","OD7F"',a)
  def test_quote_errors_are_bridged_to_non_blocking_sheet(self):
    q=read('app-quote-errors.js')
    self.assertIn('showQuoteErrorSheetFromModal',q)
    self.assertIn("observer.observe(modal,{attributes:true,attributeFilter:['aria-hidden']})",q)
    self.assertIn("if(modal.getAttribute('aria-hidden')==='false') showQuoteErrorSheetFromModal()",q)
    self.assertIn("close.addEventListener('click',closeQuoteErrorSheet)",q)
    self.assertIn("document.body.classList.remove('modal-open')",q)
    self.assertIn('-webkit-overflow-scrolling:touch',q)
    self.assertIn('touch-action:manipulation',q)
  def test_broker_ttm_uses_post_wht_events_and_adjustments(self):
    a=read('app.js')
    self.assertIn('for (const e of events) {',a)
    self.assertIn('const net = e.type === "DIVIDEND_ADJ" ? rawNet : Math.max(0, rawNet);',a)
    self.assertIn('const BROKER_REBUILD_SCHEMA_VERSION = 45;',a)
  def test_real_t212_semantics_examples(self):
    # Source-file ground truth: Total is gross EUR, WHT is native and converted once.
    pfe_gross=5.23; pfe_tax_usd=1.00; pfe_fx=0.924978
    self.assertAlmostEqual(pfe_gross-pfe_tax_usd*pfe_fx,4.305022,places=6)
    mpt_gross=1.96; mpt_tax_usd=.41; mpt_fx=.856201
    self.assertAlmostEqual(mpt_gross-mpt_tax_usd*mpt_fx,1.60895759,places=6)
    norm=read('app-broker-normalization.js')
    self.assertIn('amount` from broker import is GROSS',norm)
    self.assertIn('parseNum(d.amount) - tax',norm)
  def test_bundle_generation(self):
    i=read('index.html'); sw=read('sw.js')
    self.assertIn('app-broker-parsing-core.js?v=1.1',i)
    self.assertIn('app-asset-identity.js?v=20260829v2',i)
    self.assertIn('app.js?v=20260827v21',i)
    self.assertIn('Vestra Service Worker v10.11',sw)
    self.assertIn('vestra-cache-v125',sw)
    self.assertIn('./market-live-overlay.js',sw)
if __name__=='__main__': unittest.main(verbosity=2)
