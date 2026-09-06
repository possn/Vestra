from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
class DividendReconciliationTests(unittest.TestCase):
  def test_engine_and_rebuild(self):
    n=read('app-broker-normalization.js'); a=read('app.js')
    self.assertIn('function reconcileBrokerDividends',n)
    self.assertIn('reconcileBrokerDividends(events, state.dividends)',a)
    self.assertIn('brokerDividendReconciliation',a)
  def test_visible_card(self):
    a=read('app.js')
    self.assertIn('function renderBrokerDividendReconciliationCard',a)
    self.assertIn('Reconciliação das corretoras',a)
    self.assertIn('Delta Vestra vs eventos',a)
    self.assertIn('renderBrokerDividendReconciliationCard();',a)
  def test_bundle(self):
    i=read('index.html'); sw=read('sw.js')
    self.assertIn('app-broker-normalization.js?v=1.1',i)
    self.assertIn('app.js?v=20260827v21',i)
    self.assertIn('Vestra Service Worker v10.13',sw)
    self.assertIn('vestra-cache-v127',sw)
    self.assertIn('staleWhileRevalidate',sw)
    self.assertIn('./market-live-overlay.js',sw)
if __name__=='__main__': unittest.main(verbosity=2)
