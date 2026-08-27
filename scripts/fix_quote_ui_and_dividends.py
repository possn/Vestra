from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def read(p): return (ROOT / p).read_text(encoding='utf-8')
def write(p,s): (ROOT / p).write_text(s, encoding='utf-8')
def once(s,o,n,label):
    c=s.count(o)
    if c != 1: raise SystemExit(f'{label}: expected 1 occurrence, found {c}')
    return s.replace(o,n,1)

# 1) Canonical broker identity — venue-aware mappings must live at the source.
core = read('app-broker-parsing-core.js')
core = core.replace('"AT0000A3EPA4|AMS": "AMS2.VI"', '"AT0000A3EPA4|AMS": "AMS.SW"')
core = core.replace('"AT0000A3EPA4|AMS-OSRAM": "AMS2.VI"', '"AT0000A3EPA4|AMS-OSRAM": "AMS.SW"')
core = core.replace('"|MPW.US": "MPW"', '"|MPW.US": "MPT"')
core = once(core,
'''  if ((t === "AMS" || /\\bAMS[ -]OSRAM\\b/.test(n)) && (ccy === "CHF" || i === "AT0000A3EPA4")) return "AMS2.VI";''',
'''  if ((t === "AMS" || /\\bAMS[ -]OSRAM\\b/.test(n)) && (ccy === "CHF" || i === "AT0000A3EPA4")) return "AMS.SW";
  if ((t === "EDV" || /\\bENDEAVOUR MINING\\b/.test(n)) && ccy === "CAD") return "EDV.TO";
  if ((t === "NEO" || /\\bNEO PERFORMANCE MATERIALS\\b/.test(n)) && ccy === "CAD") return "NEO.TO";''', 'venue overrides')
core = once(core,
'''  if (t === "MPW.US" || (t === "MPW" && ccy === "USD")) return "MPW";''',
'''  if (t === "MPW.US" || t === "MPW" || /\\bMEDICAL PROPERTIES TRUST\\b/.test(n)) return "MPT";''', 'MPT rename')
write('app-broker-parsing-core.js', core)

identity = read('app-asset-identity.js')
identity = identity.replace('"AT0000A3EPA4":"AMS2.VI"', '"AT0000A3EPA4":"AMS.SW"')
identity = identity.replace('"CA64046G1063":"NEO"', '"CA64046G1063":"NEO.TO"')
if '"US58463J3041":"MPT"' not in identity:
    anchor='"US58933Y1055":"MRK"'
    if anchor not in identity: raise SystemExit('MPT ISIN insertion anchor missing')
    identity=identity.replace(anchor, '"US58463J3041":"MPT",\n  '+anchor, 1)
write('app-asset-identity.js', identity)

app = read('app.js')
# Force a broker rebuild so stale generated dividends/yahoo identities are regenerated.
app = once(app, 'const BROKER_REBUILD_SCHEMA_VERSION = 44;', 'const BROKER_REBUILD_SCHEMA_VERSION = 45;', 'broker schema')

# Generated broker assets must use venue-aware identity rather than raw ISIN mapping.
old='''    const truth = ISIN_YAHOO_MAP[String(a.isin).toUpperCase().trim()];
    if (!truth) continue;'''
new='''    const truth = a.generatedFromBroker
      ? inferYahooTickerFromIdentity({ ...a, yahooTicker: "" })
      : ISIN_YAHOO_MAP[String(a.isin).toUpperCase().trim()];
    if (!truth) continue;'''
app = once(app, old, new, 'repairYahooTickers venue-aware truth')

# Quote sanity must not compare a freshly corrected identity to stale history from the old identity.
app = once(app,
'function quoteSanityCheck(asset, q, priceEur, rawTicker) {',
'function quoteSanityCheck(asset, q, priceEur, rawTicker, previousYahooTicker = "") {', 'sanity signature')
app = once(app,
'''  const ref = historical > 0 ? historical : baseline;
  if (ref > 0) {''',
'''  const prevIdentity = String(previousYahooTicker || "").trim().toUpperCase();
  const nextIdentity = String(rawTicker || "").trim().toUpperCase();
  const identityChanged = !!(prevIdentity && nextIdentity && prevIdentity !== nextIdentity && explicit);
  // A corrected venue/ticker must not be compared to a price stored under the old identity.
  // The new quote still passed ticker/ISIN resolution and currency guards; from the next refresh
  // onward it becomes the new historical baseline.
  const ref = identityChanged ? 0 : (historical > 0 ? historical : baseline);
  if (ref > 0) {''', 'identity-aware price baseline')

old='''    const _isinTrue = ISIN_YAHOO_MAP[String(asset.isin || "").toUpperCase().trim()] || "";
    if (_isinTrue && String(yahoo || "").toUpperCase() !== String(_isinTrue).toUpperCase()) {
      console.warn("[Quote] ignoring", yahoo, "for", asset.name, "— ISIN says", _isinTrue);
      asset.yahooTicker = _isinTrue;
    } else {
      asset.yahooTicker = yahoo || asset.yahooTicker || "";
    }
    const ccy = (q.currency||"EUR").toUpperCase();'''
new='''    const _previousYahooTicker = String(asset.yahooTicker || "").trim().toUpperCase();
    const _identityTrue = asset.generatedFromBroker
      ? inferYahooTickerFromIdentity({ ...asset, yahooTicker: "" })
      : (ISIN_YAHOO_MAP[String(asset.isin || "").toUpperCase().trim()] || "");
    const _resolvedYahoo = _identityTrue || yahoo || asset.yahooTicker || "";
    if (_identityTrue && String(yahoo || "").toUpperCase() !== String(_identityTrue).toUpperCase()) {
      console.warn("[Quote] venue-aware identity", _identityTrue, "preferred over", yahoo, "for", asset.name);
    }
    const ccy = (q.currency||"EUR").toUpperCase();'''
app = once(app, old, new, 'defer yahoo identity write')
app = once(app,
'''    const sanity = quoteSanityCheck(asset, q, priceEur, yahoo || raw);''',
'''    const sanity = quoteSanityCheck(asset, q, priceEur, _resolvedYahoo || yahoo || raw, _previousYahooTicker);''', 'sanity call')
app = once(app,
'''    if (asset.generatedFromBroker && ccy) asset.priceCurrency = ccy;''',
'''    asset.yahooTicker = _resolvedYahoo || yahoo || asset.yahooTicker || "";
    if (asset.generatedFromBroker && ccy) asset.priceCurrency = ccy;''', 'store identity after sanity')

# WTI/OD7F is known closed/no-current-Yahoo in the imported ledger; skip the plain canonical too.
app = app.replace('"DN3.DE","OD7F.DE",   // delisted/no Yahoo data', '"DN3.DE","OD7F.DE","OD7F",   // delisted/no Yahoo data')

# Dividend TTM must use post-WHT normalized events, not the original bd.events.
old='''  for (const e of (bd.events || [])) {
    if (!(e && (e.type === "DIVIDEND" || e.type === "ROC" || e.type === "DIVIDEND_ADJ"))) continue;
    if (String(e.date || "") < cutoffDiv12m) continue;
    const secKey = makeBrokerSecurityKey(e);
    if (!secKey) continue;
    const net = Math.max(0, parseNum(e.totalEUR) - parseNum(e.taxEUR));
    if (net <= 0) continue;
    divNet12mBySecurity.set(secKey, (divNet12mBySecurity.get(secKey) || 0) + net);
    const ym = String(e.date || "").slice(0, 7);
    if (ym) {'''
new='''  for (const e of events) {
    if (!(e && (e.type === "DIVIDEND" || e.type === "ROC" || e.type === "DIVIDEND_ADJ"))) continue;
    if (String(e.date || "") < cutoffDiv12m) continue;
    const secKey = makeBrokerSecurityKey(e);
    if (!secKey) continue;
    const rawNet = parseNum(e.totalEUR) - parseNum(e.taxEUR);
    const net = e.type === "DIVIDEND_ADJ" ? rawNet : Math.max(0, rawNet);
    if (net === 0) continue;
    divNet12mBySecurity.set(secKey, (divNet12mBySecurity.get(secKey) || 0) + net);
    const ym = String(e.date || "").slice(0, 7);
    if (ym && net > 0) {'''
app = once(app, old, new, 'post-WHT TTM dividend events')

# Quote errors: inline panel only; never stack the legacy modal on top (iOS body lock).
app = app.replace("    openModal('modalQuoteErrors');\n", "    const panel = document.getElementById('quoteErrorsInline');\n    if (panel && panel.scrollIntoView) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });\n")
app = app.replace('          openModal("modalQuoteErrors");\n', "          quoteErrorsInlineOpen = true;\n          renderQuoteErrorsInline(true);\n          const panel = document.getElementById('quoteErrorsInline');\n          if (panel && panel.scrollIntoView) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });\n")

write('app.js', app)

# CSS: keep a bounded native-scrolling error list on iOS.
css = read('styles.css')
marker='''\n/* Vestra quote errors inline mobile scrolling */\n.quote-errors-inline__list {\n  max-height: min(56vh, 520px);\n  overflow-y: auto;\n  overscroll-behavior: contain;\n  -webkit-overflow-scrolling: touch;\n}\n'''
if 'Vestra quote errors inline mobile scrolling' not in css:
    css += marker
write('styles.css', css)

# Cache bust all touched runtime modules.
idx=read('index.html')
idx=idx.replace('app-asset-identity.js?v=1.0','app-asset-identity.js?v=1.1')
idx=idx.replace('app-broker-parsing-core.js?v=1.0','app-broker-parsing-core.js?v=1.1')
idx=idx.replace('app.js?v=20260827v19','app.js?v=20260827v20')
idx=idx.replace('styles.css?v=20260821v7','styles.css?v=20260827v8')
write('index.html',idx)

sw=read('sw.js')
sw=sw.replace('Vestra Service Worker v10.8','Vestra Service Worker v10.9')
sw=sw.replace('vestra-cache-v122','vestra-cache-v123')
write('sw.js',sw)

# Update existing generation-sensitive tests.
for p in (ROOT/'tests').glob('test_*.py'):
    s=p.read_text(encoding='utf-8')
    s=s.replace('app-asset-identity.js?v=1.0','app-asset-identity.js?v=1.1')
    s=s.replace('app-broker-parsing-core.js?v=1.0','app-broker-parsing-core.js?v=1.1')
    s=s.replace('app.js?v=20260827v19','app.js?v=20260827v20')
    s=s.replace('styles.css?v=20260821v7','styles.css?v=20260827v8')
    s=s.replace('Vestra Service Worker v10.8','Vestra Service Worker v10.9')
    s=s.replace('vestra-cache-v122','vestra-cache-v123')
    p.write_text(s,encoding='utf-8')

(ROOT/'tests/test_quote_ui_dividend_repair.py').write_text(r'''from pathlib import Path
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
    self.assertIn('identityChanged ? 0 :',a)
    self.assertIn('_previousYahooTicker',a)
    self.assertIn('asset.yahooTicker = _resolvedYahoo',a)
    self.assertIn('"OD7F.DE","OD7F"',a)
  def test_quote_errors_are_inline_not_modal_locked(self):
    a=read('app.js'); css=read('styles.css')
    self.assertNotIn("openModal('modalQuoteErrors')",a)
    self.assertNotIn('openModal("modalQuoteErrors")',a)
    self.assertIn("scrollIntoView({ behavior: 'smooth', block: 'start' })",a)
    self.assertIn('quote-errors-inline__list',css)
    self.assertIn('-webkit-overflow-scrolling: touch',css)
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
    self.assertIn('app-asset-identity.js?v=1.1',i)
    self.assertIn('app.js?v=20260827v20',i)
    self.assertIn('Vestra Service Worker v10.9',sw)
    self.assertIn('vestra-cache-v123',sw)
if __name__=='__main__': unittest.main(verbosity=2)
''',encoding='utf-8')
print('quote UI + broker dividend repair prepared')
