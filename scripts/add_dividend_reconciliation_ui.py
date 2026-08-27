from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,o,n,l):
    c=s.count(o)
    if c!=1: raise SystemExit(f'{l}: expected 1, found {c}')
    return s.replace(o,n,1)

app=read('app.js')
app=once(app,
'''const { divFloor, getDividendGross, getDividendNet, normalizeDividendRecord } = window.VestraBrokerNormalization || {};
if (![divFloor, getDividendGross, getDividendNet, normalizeDividendRecord].every(fn => typeof fn === "function")) {''',
'''const { divFloor, getDividendGross, getDividendNet, normalizeDividendRecord, reconcileBrokerDividends } = window.VestraBrokerNormalization || {};
if (![divFloor, getDividendGross, getDividendNet, normalizeDividendRecord, reconcileBrokerDividends].every(fn => typeof fn === "function")) {''','normalization import')

marker='''  // strip internal helper fields
  for (const d of state.dividends) { if (d && "secKey" in d) { delete d.secKey; delete d.divBroker; } }'''
replacement='''  // Reconcile the generated dividend ledger against the normalized broker events
  // before removing internal broker identity fields. This is a deterministic
  // accounting check: source gross/tax/net must equal what Vestra stored.
  if (!state.settings) state.settings = {};
  state.settings.brokerDividendReconciliation = reconcileBrokerDividends(events, state.dividends);

  // strip internal helper fields
  for (const d of state.dividends) { if (d && "secKey" in d) { delete d.secKey; delete d.divBroker; } }'''
app=once(app,marker,replacement,'reconciliation snapshot')

render_fn=r'''
function renderBrokerDividendReconciliationCard() {
  const host = document.getElementById("paneDivSummary") || document.getElementById("viewDividends");
  if (!host) return;
  let card = document.getElementById("brokerDividendReconciliationCard");
  const report = (((state || {}).settings || {}).brokerDividendReconciliation) || null;
  if (!report || !Array.isArray(report.rows) || !report.rows.length) {
    if (card) card.remove();
    return;
  }
  if (!card) {
    card = document.createElement("div");
    card.id = "brokerDividendReconciliationCard";
    card.className = "card";
    card.style.cssText = "margin-bottom:14px";
    host.insertBefore(card, host.firstChild || null);
  }
  const t = report.totals || {};
  const ok = !!report.ok;
  const rows = report.rows.map(r => `
    <div style="display:grid;grid-template-columns:minmax(90px,1fr) repeat(3,minmax(76px,.8fr));gap:8px;padding:8px 0;border-top:1px solid var(--line);align-items:center">
      <div><div style="font-weight:800;font-size:12px">${escapeHtml(r.broker || "Corretora")}</div><div style="font-size:11px;color:var(--muted)">${escapeHtml(r.year || "")}</div></div>
      <div style="text-align:right"><div style="font-size:10px;color:var(--muted)">Bruto</div><b style="font-size:12px">${fmtEUR2(r.storedGross || 0)}</b></div>
      <div style="text-align:right"><div style="font-size:10px;color:var(--muted)">Imposto</div><b style="font-size:12px">${fmtEUR2(r.storedTax || 0)}</b></div>
      <div style="text-align:right"><div style="font-size:10px;color:var(--muted)">Δ líquido</div><b style="font-size:12px;color:${Math.abs(r.deltaNet || 0)<.011?'#059669':'#dc2626'}">${fmtEUR2(r.deltaNet || 0)}</b></div>
    </div>`).join("");
  card.innerHTML = `
    <div class="card__head" style="margin-bottom:8px">
      <div>
        <div class="card__title">${ok ? "✅" : "⚠️"} Reconciliação das corretoras</div>
        <div class="card__muted">Eventos importados → dividendos Vestra · bruto, retenção e líquido</div>
      </div>
      <span class="badge ${ok ? 'badge--green' : ''}" style="white-space:nowrap">${ok ? 'Delta 0' : 'Rever delta'}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0 4px">
      <div style="background:var(--card2);border-radius:10px;padding:8px;text-align:center"><small style="color:var(--muted)">Bruto fonte</small><div style="font-weight:900">${fmtEUR2(t.sourceGross || 0)}</div></div>
      <div style="background:var(--card2);border-radius:10px;padding:8px;text-align:center"><small style="color:var(--muted)">Retenção</small><div style="font-weight:900">${fmtEUR2(t.sourceTax || 0)}</div></div>
      <div style="background:var(--card2);border-radius:10px;padding:8px;text-align:center"><small style="color:var(--muted)">Líquido fonte</small><div style="font-weight:900">${fmtEUR2(t.sourceNet || 0)}</div></div>
    </div>
    <div style="font-size:11px;color:var(--muted);margin:8px 0">Delta Vestra vs eventos: bruto ${fmtEUR2(t.deltaGross || 0)} · imposto ${fmtEUR2(t.deltaTax || 0)} · líquido ${fmtEUR2(t.deltaNet || 0)}</div>
    ${rows}`;
}
'''
app=once(app,'\nfunction renderDividends() {',render_fn+'\nfunction renderDividends() {','reconciliation render function')
app=once(app,
'''function renderDividends() {
  // Show/hide panes based on mode''',
'''function renderDividends() {
  renderBrokerDividendReconciliationCard();
  // Show/hide panes based on mode''','render call')
write('app.js',app)

idx=read('index.html')
idx=idx.replace('app-broker-normalization.js?v=1.0','app-broker-normalization.js?v=1.1')
idx=idx.replace('app.js?v=20260827v20','app.js?v=20260827v21')
write('index.html',idx)
sw=read('sw.js').replace('Vestra Service Worker v10.9','Vestra Service Worker v10.10').replace('vestra-cache-v123','vestra-cache-v124')
write('sw.js',sw)

for p in (ROOT/'tests').glob('test_*.py'):
    s=p.read_text(encoding='utf-8').replace('app-broker-normalization.js?v=1.0','app-broker-normalization.js?v=1.1').replace('app.js?v=20260827v20','app.js?v=20260827v21').replace('Vestra Service Worker v10.9','Vestra Service Worker v10.10').replace('vestra-cache-v123','vestra-cache-v124')
    p.write_text(s,encoding='utf-8')

(ROOT/'tests/test_dividend_reconciliation.py').write_text(r'''from pathlib import Path
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
    self.assertIn('Vestra Service Worker v10.10',sw)
    self.assertIn('vestra-cache-v124',sw)
if __name__=='__main__': unittest.main(verbosity=2)
''',encoding='utf-8')
print('dividend reconciliation UI prepared')
