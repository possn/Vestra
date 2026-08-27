from pathlib import Path

APP=Path('app.js')
INDEX=Path('index.html')
SW=Path('sw.js')
app=APP.read_text()
index=INDEX.read_text()
sw=SW.read_text()

old="const { fetchQuote, fetchFxRates, mapWithConcurrency, FX_FALLBACK_LOCAL } = window.VestraMarketClient || {};\nif (![fetchQuote, fetchFxRates, mapWithConcurrency].every(fn => typeof fn === 'function') || !FX_FALLBACK_LOCAL) {"
new="const { fetchQuote, fetchQuotesBatch, fetchFxRates, mapWithConcurrency, FX_FALLBACK_LOCAL } = window.VestraMarketClient || {};\nif (![fetchQuote, fetchQuotesBatch, fetchFxRates, mapWithConcurrency].every(fn => typeof fn === 'function') || !FX_FALLBACK_LOCAL) {"
assert app.count(old)==1, 'market client import marker changed'
app=app.replace(old,new)

old_block='''  // Proven architecture from the former Património app: each asset resolves its\n  // own Yahoo candidates through /quote. Bounded concurrency avoids launching\n  // hundreds of simultaneous requests while preserving per-asset fallbacks.\n  const quoteResults = await mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x));\n  const quoteMap = {};\n  const quoteErrMap = {};\n  quoteResults.forEach((r, i) => {\n    if (r && r.status === "fulfilled" && r.value && r.value.quote) quoteMap[i] = r.value;\n    else quoteErrMap[i] = (r && r.reason && r.reason.message) ? r.reason.message : "Erro ao obter cotação";\n  });'''
new_block='''  // Batch-first transport: one POST /quotes handles up to 80 tickers.\n  // Individual /quote calls are now reserved for alternate candidates or\n  // compatibility with an older Worker that does not expose /quotes yet.\n  const quoteMap = {};\n  const quoteErrMap = {};\n  const firstByIndex = tickerList.map(ref => (ref.candidates || [])[0] || "");\n  const uniqueFirst = [...new Set(firstByIndex.filter(Boolean))];\n  let batchUnsupported = false;\n  let batchResult = { quotes:{}, errors:{} };\n  try {\n    batchResult = await fetchQuotesBatch(uniqueFirst, workerUrl, 9000);\n    batchUnsupported = !!batchResult.unsupported;\n  } catch (e) {\n    console.warn('[Quotes batch] failed', e);\n    batchResult = { quotes:{}, errors:{} };\n  }\n\n  const fallbackIndexes = [];\n  tickerList.forEach((ref, i) => {\n    const first = firstByIndex[i];\n    const q = first && batchResult.quotes && batchResult.quotes[first];\n    if (q && Number.isFinite(Number(q.price)) && Number(q.price) > 0 && isQuoteCandidateAcceptable(ref.asset, first)) {\n      quoteMap[i] = { yahoo:first, quote:q };\n      return;\n    }\n    // If batch is unsupported, preserve the legacy path for every asset.\n    // Otherwise retry only assets with alternate candidates; a network-failed\n    // first candidate is not hammered again hundreds of times.\n    const remaining = batchUnsupported ? (ref.candidates || []) : (ref.candidates || []).slice(1);\n    if (remaining.length) fallbackIndexes.push({ i, ref:{ ...ref, candidates:remaining } });\n    else quoteErrMap[i] = (batchResult.errors && batchResult.errors[first]) || 'Sem dados para ' + (first || ref.raw || 'ticker');\n  });\n\n  const fallbackResults = await mapWithConcurrency(fallbackIndexes, 6, x => fetchQuoteWithFallback(x.ref));\n  fallbackResults.forEach((r, j) => {\n    const idx = fallbackIndexes[j].i;\n    if (r && r.status === 'fulfilled' && r.value && r.value.quote) quoteMap[idx] = r.value;\n    else quoteErrMap[idx] = (r && r.reason && r.reason.message) ? r.reason.message : (quoteErrMap[idx] || 'Erro ao obter cotação');\n  });'''
assert app.count(old_block)==1, 'quote transport block changed'
app=app.replace(old_block,new_block)

old_open='''function openQuoteErrorDetails(reportOverride = null) {\n  const report = reportOverride || ((((state || {}).settings || {}).lastQuoteRefresh) || { updated:0, failed:0, errors:[] });\n  const errors = Array.isArray(report.errors) ? report.errors : [];\n  const failed = Number(report.failed || errors.length || 0);\n  showQuoteErrors(Number(report.updated || 0), failed, errors, Number(report.updated || 0), failed);\n  // Explicit user action must always open a visible surface in the current view.\n  // The inline list belongs to Carteira and is hidden while the user is in Mais.\n  openModal('modalQuoteErrors');\n}'''
new_open='''function closeQuoteErrorDetails() {\n  const modal = document.getElementById('modalQuoteErrors');\n  if (!modal) return;\n  modal.classList.remove('modal--open');\n  modal.setAttribute('aria-hidden','true');\n  modal.style.display = 'none';\n  document.body.classList.remove('modal-open');\n}\n\nfunction openQuoteErrorDetails(reportOverride = null) {\n  const report = reportOverride || ((((state || {}).settings || {}).lastQuoteRefresh) || { updated:0, failed:0, errors:[] });\n  const errors = Array.isArray(report.errors) ? report.errors : [];\n  const failed = Number(report.failed || errors.length || 0);\n  showQuoteErrors(Number(report.updated || 0), failed, errors, Number(report.updated || 0), failed);\n  const modal = document.getElementById('modalQuoteErrors');\n  if (!modal) return;\n  const panel = modal.querySelector('.modal__panel');\n  const head = modal.querySelector('.modal__head');\n  const body = modal.querySelector('.modal__body');\n  // Dedicated non-locking sheet. Safari/iOS can scroll the list independently\n  // and the close control is never hidden behind a body scroll lock.\n  modal.style.cssText += ';display:flex;position:fixed;inset:0;z-index:1200;align-items:flex-end;background:rgba(15,23,42,.38);padding:12px 10px max(10px,env(safe-area-inset-bottom));';\n  if (panel) panel.style.cssText += ';width:min(760px,100%);max-height:calc(100dvh - 24px);margin:0 auto;display:flex;flex-direction:column;overflow:hidden;border-radius:24px 24px 18px 18px;';\n  if (head) head.style.cssText += ';position:sticky;top:0;z-index:3;flex:0 0 auto;background:var(--card,#fff);';\n  if (body) body.style.cssText += ';overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;flex:1 1 auto;min-height:0;padding-bottom:max(24px,env(safe-area-inset-bottom));';\n  modal.setAttribute('aria-hidden','false');\n  document.body.classList.remove('modal-open');\n  if (body) body.scrollTop = 0;\n}'''
assert app.count(old_open)==1, 'quote error opener changed'
app=app.replace(old_open,new_open)

# Add strong, capture-phase close wiring once after inline close wiring.
marker='''  const btnQuoteErrorsInlineClose = $("btnQuoteErrorsInlineClose");\n  if (btnQuoteErrorsInlineClose) btnQuoteErrorsInlineClose.addEventListener("click", () => { quoteErrorsInlineOpen = false; renderQuoteErrorsInline(false); });'''
insert=marker+'''\n  const quoteErrModal = document.getElementById('modalQuoteErrors');\n  const quoteErrClose = quoteErrModal && quoteErrModal.querySelector('[data-close]');\n  if (quoteErrClose && !quoteErrClose.dataset.quoteCloseWired) {\n    quoteErrClose.dataset.quoteCloseWired = '1';\n    quoteErrClose.addEventListener('click', e => { e.preventDefault(); e.stopImmediatePropagation(); closeQuoteErrorDetails(); }, true);\n  }\n  if (quoteErrModal && !quoteErrModal.dataset.quoteBackdropWired) {\n    quoteErrModal.dataset.quoteBackdropWired = '1';\n    quoteErrModal.addEventListener('click', e => { if (e.target === quoteErrModal) { e.preventDefault(); closeQuoteErrorDetails(); } }, true);\n  }'''
assert app.count(marker)==1, 'quote close wiring marker changed'
app=app.replace(marker,insert)

old_mode='state.settings.lastQuoteRefresh = { updated, failed, skipped, errors, workerMode:"individual", ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };'
new_mode='state.settings.lastQuoteRefresh = { updated, failed, skipped, errors, workerMode: batchUnsupported ? "individual" : "batch", ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };'
assert app.count(old_mode)==1, 'workerMode marker changed'
app=app.replace(old_mode,new_mode)

# Cache-bust runtime files.
assert 'app-market-client.js?v=1.0' in index
assert 'app.js?v=20260827v21' in index
index=index.replace('app-market-client.js?v=1.0','app-market-client.js?v=1.1')
index=index.replace('app.js?v=20260827v21','app.js?v=20260827v22')
# Also surface the already-published routing v1.1 rather than stale query string.
index=index.replace('portfolio-dossier-routing.js?v=1.0','portfolio-dossier-routing.js?v=1.1')

assert 'Service Worker v10.10' in sw and 'vestra-cache-v124' in sw
sw=sw.replace('Service Worker v10.10','Service Worker v10.11').replace('vestra-cache-v124','vestra-cache-v125')

APP.write_text(app)
INDEX.write_text(index)
SW.write_text(sw)
print('patched quote batch transport + non-locking error sheet')
