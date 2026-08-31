from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    text = path.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'expected text not found in {path}')
    if text.count(old) != 1:
        raise SystemExit(f'expected exactly one match in {path}, got {text.count(old)}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


# 1) market.js: retain stable function names but delegate implementation to the new module.
market = ROOT / 'market.js'
text = market.read_text(encoding='utf-8')
start = text.find('  function workerBase(){')
end_marker = '\n\n\n\n  function normalizeCongressLive'
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('live overlay block boundaries not found in market.js')
old_block = text[start:end]
if 'async function enrichTickerLive' not in old_block or 'refreshOpenDossierLiveFields' not in old_block:
    raise SystemExit('market.js live overlay block does not match expected contract')
new_block = '''  function workerBase(){
    try { return txt(typeof state!=='undefined' && state?.settings?.workerUrl).replace(/\\/$/,''); } catch { return ''; }
  }
  const marketLiveOverlay=window.VestraMarketLiveOverlay?.create({
    getWorkerBase:workerBase,
    getSheet:()=> $m('marketSheet'),
    loadingSet:M.liveLoading,
    text:txt,
    escapeHtml:esc,
    formatMoney:money,
    formatNum:num,
    formatPct:pct,
  })||null;
  function compactLiveBadge(s){ return marketLiveOverlay?.compactLiveBadge(s)||''; }
  function refreshOpenDossierLiveFields(s){ return marketLiveOverlay?.refreshOpenDossierLiveFields(s); }
  async function enrichTickerLive(s){ return marketLiveOverlay?.enrichTickerLive(s)??null; }
'''
market.write_text(text[:start] + new_block + text[end:], encoding='utf-8')

# 2) index.html: module must load before market.js because market.js binds the delegate at startup.
replace_once(
    ROOT / 'index.html',
    '<script defer="" src="market.js?v=20260830v1"></script>',
    '<script defer="" src="market-live-overlay.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v1"></script>'
)

# 3) Service Worker: keep new static module available to the PWA shell.
sw = ROOT / 'sw.js'
sw_text = sw.read_text(encoding='utf-8')
sw_text = sw_text.replace('Service Worker v10.10', 'Service Worker v10.11', 1)
sw_text = sw_text.replace('vestra-cache-v124', 'vestra-cache-v125', 1)
needle = '  "./market.js",\n'
if needle not in sw_text:
    raise SystemExit('market.js cache entry not found in sw.js')
sw_text = sw_text.replace(needle, needle + '  "./market-live-overlay.js",\n', 1)
sw.write_text(sw_text, encoding='utf-8')

# 4) Architecture CI: syntax + dedicated runtime contract.
workflow = ROOT / '.github/workflows/architecture-invariants.yml'
wf = workflow.read_text(encoding='utf-8')
wf = wf.replace(
    '          node --check market.js\n          node --check market-data-loader.js',
    '          node --check market-live-overlay.js\n          node --check market.js\n          node --check market-data-loader.js',
    1,
)
wf = wf.replace(
    '          node --check tests/runtime_market_data_health_contract.js\n',
    '          node --check tests/runtime_market_data_health_contract.js\n          node --check tests/runtime_market_live_overlay_contract.js\n',
    1,
)
anchor = '      - name: Runtime · market data health semantics\n        run: node tests/runtime_market_data_health_contract.js\n'
if anchor not in wf:
    raise SystemExit('market data health runtime step not found in architecture workflow')
wf = wf.replace(
    anchor,
    anchor + '      - name: Runtime · market live overlay\n        run: node tests/runtime_market_live_overlay_contract.js\n',
    1,
)
workflow.write_text(wf, encoding='utf-8')

# 5) Runtime regression expectations move from implementation-in-market.js to delegation contract.
tests = ROOT / 'tests/test_runtime_regressions.py'
t = tests.read_text(encoding='utf-8')
t = t.replace(
    '            "app.js", "market.js", "market-data-loader.js", "politicians.js", "worker.js",',
    '            "app.js", "market-live-overlay.js", "market.js", "market-data-loader.js", "politicians.js", "worker.js",',
    1,
)
old_method = '''    def test_market_live_overlay_does_not_rerender_open_dossier(self):
        market = read("market.js")
        self.assertIn("refreshOpenDossierLiveFields", market)
        self.assertIn('data-live-field="current_price"', market)
        self.assertIn('data-live-field="forward_pe"', market)
        self.assertIn('data-live-field="roe"', market)
        self.assertIn('data-live-field="revenue_growth"', market)
        self.assertIn('data-live-field="fcf_yield"', market)
'''
new_method = '''    def test_market_live_overlay_does_not_rerender_open_dossier(self):
        market = read("market.js")
        overlay = read("market-live-overlay.js")
        html = read("index.html")
        sw = read("sw.js")
        self.assertIn("VestraMarketLiveOverlay?.create", market)
        self.assertIn("marketLiveOverlay?.enrichTickerLive", market)
        self.assertIn("marketLiveOverlay?.refreshOpenDossierLiveFields", market)
        self.assertNotIn("Object.assign(s,merge,{_liveUpdated", market)
        for field in ("current_price", "forward_pe", "roe", "revenue_growth", "fcf_yield"):
            self.assertIn(field, overlay)
        self.assertNotIn("marketSheetContent", overlay)
        self.assertLess(html.find("market-live-overlay.js"), html.find("market.js"))
        self.assertIn('"./market-live-overlay.js"', sw)
'''
if old_method not in t:
    raise SystemExit('old live overlay regression test not found')
t = t.replace(old_method, new_method, 1)
tests.write_text(t, encoding='utf-8')

print('market live overlay refactor applied')
