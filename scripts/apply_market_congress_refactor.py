from pathlib import Path

root = Path(__file__).resolve().parents[1]
market_path = root / 'market.js'
index_path = root / 'index.html'
sw_path = root / 'sw.js'

market = market_path.read_text(encoding='utf-8')
start = market.index('  function normalizeCongressLive(x){')
end = market.index("\n\n  const WATCH_KEY = 'vestra-market-watchlist-v1';", start)
old = market[start:end]
if 'async function loadCongressLive' not in old or 'attachCongressToStocks' not in old:
    raise SystemExit('guard failed: expected Congress block not found')

replacement = '''  const congressLiveState = {};
  Object.defineProperties(congressLiveState, {
    trades: { get: () => M.congressLive, set: value => { M.congressLive = Array.isArray(value) ? value : []; } },
    loaded: { get: () => M.congressLoaded, set: value => { M.congressLoaded = Boolean(value); } },
    loading: { get: () => M.congressLoading, set: value => { M.congressLoading = value || null; } },
    error: { get: () => M.congressError, set: value => { M.congressError = txt(value); } },
  });
  const congressLiveFeed = window.VestraMarketCongressLive?.create({
    state: congressLiveState,
    getStocksByTicker: () => M.byTicker,
    getStocks: () => M.stocks,
    text: txt,
  }) || null;
  function normalizeCongressLive(x){ return congressLiveFeed?.normalize(x) || {}; }
  function politiciansSnapshotFresh(d){ return congressLiveFeed?.snapshotFresh(d) || false; }
  function attachCongressToStocks(trades){ return congressLiveFeed?.attachToStocks(trades); }
  async function loadCongressLive(ticker=''){ return congressLiveFeed?.load(ticker) ?? []; }
'''
market = market[:start] + replacement + market[end:]
market_path.write_text(market, encoding='utf-8')

index = index_path.read_text(encoding='utf-8')
needle = '<script defer="" src="market-live-overlay.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v1"></script>'
repl = '<script defer="" src="market-live-overlay.js?v=1.0"></script>\n<script defer="" src="market-congress-live.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>'
if needle not in index:
    raise SystemExit('guard failed: market script order not found')
index_path.write_text(index.replace(needle, repl, 1), encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8')
if 'Service Worker v10.11' not in sw or 'vestra-cache-v125' not in sw:
    raise SystemExit('guard failed: unexpected service worker generation')
sw = sw.replace('Service Worker v10.11', 'Service Worker v10.12', 1)
sw = sw.replace('vestra-cache-v125', 'vestra-cache-v126', 1)
needle = '  "./market-live-overlay.js",\n'
if needle not in sw:
    raise SystemExit('guard failed: live overlay shell entry not found')
sw = sw.replace(needle, needle + '  "./market-congress-live.js",\n', 1)
sw_path.write_text(sw, encoding='utf-8')
