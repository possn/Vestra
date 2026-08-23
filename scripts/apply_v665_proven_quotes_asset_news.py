from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]

# 1) Restore the proven individual quote fallback architecture from the former
# patrimônio app, but with bounded concurrency. Remove the experimental batch
# state machine entirely so Safari cannot hit TDZ/scope errors.
p=root/'app.js'
s=p.read_text(encoding='utf-8')
start=s.find('async function fetchQuoteBatch(tickers) {')
end=s.find('  // Collect currencies needing FX', start)
if start < 0 or end < 0:
    raise SystemExit('quote batch block anchors not found')
replacement=r'''async function fetchQuoteWithFallback(ref) {
  let lastErr = null;
  for (const candidate of (ref.candidates || [])) {
    try {
      if (!isQuoteCandidateAcceptable(ref.asset, candidate)) {
        lastErr = new Error(`Candidato incompatível com a identidade do ativo: ${candidate}`);
        continue;
      }
      const q = await fetchQuote(candidate, workerUrl);
      if (q && Number.isFinite(Number(q.price)) && Number(q.price) > 0) {
        return { yahoo: candidate, quote: q };
      }
      lastErr = new Error(`Sem dados para ${candidate}`);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Não foi possível obter uma cotação válida");
}

async function mapWithConcurrency(items, concurrency, fn) {
  const out = new Array(items.length);
  let cursor = 0;
  const workers = Array.from({length: Math.max(1, Math.min(concurrency, items.length || 1))}, async () => {
    while (true) {
      const idx = cursor++;
      if (idx >= items.length) return;
      try { out[idx] = {status:'fulfilled', value: await fn(items[idx], idx)}; }
      catch (reason) { out[idx] = {status:'rejected', reason}; }
    }
  });
  await Promise.all(workers);
  return out;
}

  const rawTickerRefs = candidates.map(asset => {
    const raw = getRawTickerForAsset(asset);
    return { asset, raw, candidates: buildYahooTickerCandidates(asset) };
  });
  const noCandidateRefs = rawTickerRefs.filter(x => !(x.candidates && x.candidates.length));
  const tickerList = rawTickerRefs.filter(x => x.candidates && x.candidates.length);
  let skipped = 0;
  noCandidateRefs.forEach(ref => {
    const rawUp = String(ref.raw || "").toUpperCase().trim();
    const baseUp = canonicalBrokerTickerBase(rawUp);
    if (SKIP_TICKERS.has(rawUp) || SKIP_TICKERS.has(baseUp)) { skipped++; return; }
    // No safe market identity is not a quote failure. Keep the last known value.
    skipped++;
  });

  // Proven architecture from the former Património app: each asset resolves its
  // own Yahoo candidates through /quote. Bounded concurrency avoids launching
  // hundreds of simultaneous requests while preserving per-asset fallbacks.
  const quoteResults = await mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x));
  const quoteMap = {};
  const quoteErrMap = {};
  quoteResults.forEach((r, i) => {
    if (r && r.status === "fulfilled" && r.value && r.value.quote) quoteMap[i] = r.value;
    else quoteErrMap[i] = (r && r.reason && r.reason.message) ? r.reason.message : "Erro ao obter cotação";
  });

'''
s=s[:start]+replacement+s[end:]
# Remove any experimental quoteWorkerMode declarations/usages left elsewhere.
s=re.sub(r'^\s*let quoteWorkerMode\s*=.*?;\s*$', '', s, flags=re.M)
s=re.sub(r'^\s*quoteWorkerMode\s*=.*?;\s*$', '', s, flags=re.M)
s=s.replace('mode: quoteWorkerMode, ', '')
s=s.replace(', mode: quoteWorkerMode', '')
s=s.replace('quoteWorkerMode === "single" ? "compatibilidade" : "batch"', '"individual"')
s=s.replace('quoteWorkerMode === \'single\' ? \'compatibilidade\' : \'batch\'', "'individual'")
# Ensure report has skipped and no undeclared mode variable.
old='state.settings.lastQuoteRefresh = { updated, failed, errors, ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };'
new='state.settings.lastQuoteRefresh = { updated, failed, skipped, errors, mode:"individual", ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };'
if old in s: s=s.replace(old,new,1)
# Status copy: expose skipped without calling them errors.
s=s.replace('meta.textContent = `${report.updated || 0} atualizadas · ${report.failed} com erro${secs}`;', 'meta.textContent = `${report.updated || 0} atualizadas · ${report.failed} com erro${report.skipped ? ` · ${report.skipped} ignoradas` : ""}${secs}`;')
s=s.replace('meta.textContent = `${report.updated} atualizadas${secs} · automático`;', 'meta.textContent = `${report.updated} atualizadas${report.skipped ? ` · ${report.skipped} ignoradas` : ""}${secs} · automático`;')
# Cache bump.
s=s.replace('sw.js?v=20260509v67','sw.js?v=20260509v68')
p.write_text(s,encoding='utf-8')

# 2) Rewrite news generation so ticker ambiguity cannot produce unrelated stories.
p=root/'scripts/news.py'
p.write_text(r'''"""Ticker-specific company news, fetched server-side during the daily pipeline."""
from __future__ import annotations

import datetime
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

log = logging.getLogger("news")
HEADERS = {"User-Agent": "Vestra research-tool"}
MAX_ITEMS_PER_TICKER = 6
MAX_WORKERS = 12
REQUEST_TIMEOUT = 8

_STOP = {"inc","inc.","corp","corp.","corporation","company","co","co.","plc","ltd","limited","sa","se","ag","nv","holdings","holding","group","the","class"}

def _tokens(name: str) -> list[str]:
    words=re.findall(r"[A-Za-z0-9]+", name or "")
    return [w.lower() for w in words if len(w)>=3 and w.lower() not in _STOP][:5]

def _relevant(title: str, ticker: str, name: str) -> bool:
    text=(title or "").lower()
    base=ticker.split(".")[0].lower()
    toks=_tokens(name)
    # Company-name evidence is strongest. Require at least one meaningful name token.
    if toks and any(t in text for t in toks): return True
    # Ticker-only matching is allowed only for unambiguous tickers (>=3 chars),
    # and must be a standalone token to avoid M/F/O-style false positives.
    if len(base)>=3 and re.search(rf"(?<![a-z0-9]){re.escape(base)}(?![a-z0-9])", text): return True
    return False

def _fetch_one(ticker: str, name: str="") -> tuple[str, list[dict]]:
    base=ticker.split(".")[0]
    query=(f'"{name}" {base} stock' if name else f'"{base}" stock')
    url=("https://news.google.com/rss/search?q="+urllib.parse.quote_plus(query)+"&hl=en-US&gl=US&ceid=US:en")
    try:
        resp=requests.get(url,headers=HEADERS,timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root=ET.fromstring(resp.content)
        items=[]
        for item in root.findall(".//item"):
            title=(item.findtext("title") or "").strip()
            link=(item.findtext("link") or "").strip()
            pub=(item.findtext("pubDate") or "").strip()
            source_el=item.find("source")
            source=source_el.text.strip() if source_el is not None and source_el.text else None
            if title and link and _relevant(title,ticker,name):
                items.append({"title":title,"link":link,"published":pub,"source":source})
            if len(items)>=MAX_ITEMS_PER_TICKER: break
        return ticker,items
    except Exception as e:
        log.debug("%s: news fetch failed (%s)",ticker,e)
        return ticker,[]

def fetch_news_for_universe(tickers: list[str], names: dict[str,str] | None=None) -> dict:
    names=names or {}
    results={}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures={pool.submit(_fetch_one,t,names.get(t,"")):t for t in tickers}
        for future in as_completed(futures):
            ticker,items=future.result()
            if items: results[ticker]=items
    log.info("news: %d/%d tickers returned relevant headlines",len(results),len(tickers))
    return {"generated_at":datetime.datetime.utcnow().isoformat()+"Z","source":"Google News RSS","note":"Company-name + ticker query with relevance filtering; dossier news is asset-specific.","tickers":results}
''',encoding='utf-8')

# 3) Pass company names to news generator.
p=root/'scripts/run.py'
s=p.read_text(encoding='utf-8')
old='news_payload = fetch_news_for_universe(all_tickers)'
new='news_payload = fetch_news_for_universe(all_tickers, {str(r.get("ticker") or ""): str(r.get("name") or "") for r in rows})'
if old not in s: raise SystemExit('run news call anchor not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# 4) Frontend defensive relevance filter: never show obviously unrelated cached stories.
p=root/'market.js'
s=p.read_text(encoding='utf-8')
old="const items=M.news?.tickers?.[s.ticker]||[];\n      body.innerHTML=`<div class=\"market-detail-card\"><h4>Notícias recentes</h4>${items.length?items.slice(0,10).map(x=>`<div class=\"market-news-item\"><a href=\"${esc(x.link)}\" target=\"_blank\" rel=\"noopener\">${esc(x.title)}</a><small>${esc(x.source||'')} · ${esc(x.published||'')}</small></div>`).join(''):'<p>Sem notícias recentes para este ticker.</p>'}</div>`;"
new="const rawItems=M.news?.tickers?.[s.ticker]||[];\n      const nameTokens=txt(s.name).toLowerCase().match(/[a-z0-9]{3,}/g)||[];\n      const baseTicker=txt(s.ticker).toLowerCase().split('.')[0];\n      const items=rawItems.filter(x=>{ const h=txt(x.title).toLowerCase(); return nameTokens.some(t=>h.includes(t)) || (baseTicker.length>=3 && new RegExp(`(^|[^a-z0-9])${baseTicker.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')}([^a-z0-9]|$)`,'i').test(h)); });\n      body.innerHTML=`<div class=\"market-detail-card\"><h4>Notícias de ${esc(s.name||s.ticker)}</h4>${items.length?items.slice(0,10).map(x=>`<div class=\"market-news-item\"><a href=\"${esc(x.link)}\" target=\"_blank\" rel=\"noopener\">${esc(x.title)}</a><small>${esc(x.source||'')} · ${esc(x.published||'')}</small></div>`).join(''):'<p>Sem notícias recentes confirmadas para este ativo.</p>'}</div>`;"
if old not in s: raise SystemExit('market news block anchor not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# README + SW
p=root/'README.md'; r=p.read_text(encoding='utf-8')
if not r.startswith('## Vestra v6.6.5'):
    r='''## Vestra v6.6.5 — Proven Quote Refresh & Asset-Specific News\n\n- Reposto o mecanismo de cotações comprovado na app Património: `/quote` individual com fallback por candidato Yahoo, agora com concorrência limitada.\n- Removido o estado experimental `quoteWorkerMode` e a dependência do endpoint batch `/quotes`.\n- Ativos sem identidade segura são ignorados, não apresentados como falhas de rede.\n- Notícias passam a pesquisar nome da empresa + ticker e a aplicar filtro de relevância.\n- A tab Notícias do dossier mostra apenas títulos confirmadamente relacionados com o ativo aberto.\n- PWA cache: `vestra-cache-v68`.\n\n'''+r
p.write_text(r,encoding='utf-8')
p=root/'sw.js'; sw=p.read_text(encoding='utf-8').replace('vestra-cache-v67','vestra-cache-v68'); p.write_text(sw,encoding='utf-8')
