from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
p=root/'app.js'
s=p.read_text()
old='''async function fetchQuoteBatch(tickers) {
  const unique = [...new Set((tickers || []).filter(Boolean))];
  if (!unique.length) return {};
  const url = `${workerUrl.replace(/\/$/, "")}/quotes?tickers=${encodeURIComponent(unique.join(","))}`;
  let resp;
  try {
    resp = await fetch(url, { signal: AbortSignal.timeout(18000) });
  } catch (e) {
    throw new Error(`Worker inacessível: ${e.message || "timeout"}`);
  }
  let data = null;
  try { data = await resp.json(); } catch (_) {}
  if (!resp.ok) throw new Error(`Worker HTTP ${resp.status}${data && data.error ? `: ${data.error}` : ""}`);
  return data || {};
}

async function fetchQuoteBatches(tickers, concurrency = 6) {
  const unique = [...new Set((tickers || []).filter(Boolean))];
  const chunks = [];
  for (let i = 0; i < unique.length; i += 20) chunks.push(unique.slice(i, i + 20));
  const out = {};
  let cursor = 0;
  const workers = Array.from({ length: Math.min(concurrency, chunks.length) }, async () => {
    while (cursor < chunks.length) {
      const idx = cursor++;
      const chunk = chunks[idx];
      try {
        Object.assign(out, await fetchQuoteBatch(chunk));
      } catch (e) {
        chunk.forEach(t => { out[t] = { ticker:t, error:e.message || "Erro" }; });
      }
    }
  });
  await Promise.all(workers);
  return out;
}
'''
new='''async function fetchQuoteBatch(tickers) {
  const unique = [...new Set((tickers || []).filter(Boolean))];
  if (!unique.length) return {};
  const url = `${workerUrl.replace(/\/$/, "")}/quotes?tickers=${encodeURIComponent(unique.join(","))}`;
  let resp;
  try {
    resp = await fetch(url, { signal: AbortSignal.timeout(18000) });
  } catch (e) {
    const err = new Error(`Worker inacessível: ${e.message || "timeout"}`);
    err.batchTransport = true;
    throw err;
  }
  let data = null;
  try { data = await resp.json(); } catch (_) {}
  if (!resp.ok) {
    const err = new Error(`Worker HTTP ${resp.status}${data && data.error ? `: ${data.error}` : ""}`);
    err.batchUnsupported = [400,404,405,501].includes(resp.status) || /endpoint|quotes/i.test(String(data && data.error || ""));
    throw err;
  }
  // A compatible /quotes endpoint must return an object keyed by requested symbols.
  if (!data || typeof data !== "object" || Array.isArray(data) || !unique.some(t => Object.prototype.hasOwnProperty.call(data, t))) {
    const err = new Error("Resposta /quotes incompatível com esta versão da app");
    err.batchUnsupported = true;
    throw err;
  }
  return data;
}

async function fetchQuotesIndividually(tickers, concurrency = 5) {
  const unique = [...new Set((tickers || []).filter(Boolean))];
  const out = {};
  let cursor = 0;
  const workers = Array.from({ length: Math.min(concurrency, unique.length) }, async () => {
    while (cursor < unique.length) {
      const ticker = unique[cursor++];
      try {
        out[ticker] = await fetchQuote(ticker, workerUrl);
      } catch (e) {
        out[ticker] = { ticker, error:e && e.message ? e.message : "Erro" };
      }
    }
  });
  await Promise.all(workers);
  return out;
}

let quoteWorkerMode = "batch";
async function fetchQuoteBatches(tickers, concurrency = 3) {
  const unique = [...new Set((tickers || []).filter(Boolean))];
  const chunks = [];
  for (let i = 0; i < unique.length; i += 20) chunks.push(unique.slice(i, i + 20));
  const out = {};
  let cursor = 0;
  const workers = Array.from({ length: Math.min(concurrency, chunks.length) }, async () => {
    while (cursor < chunks.length) {
      const idx = cursor++;
      const chunk = chunks[idx];
      // Once incompatibility is proven, stop hammering /quotes and use /quote.
      if (quoteWorkerMode === "single") {
        Object.assign(out, await fetchQuotesIndividually(chunk, 5));
        continue;
      }
      try {
        const batch = await fetchQuoteBatch(chunk);
        const successes = chunk.filter(t => {
          const q=batch[t]; return q && !q.error && Number.isFinite(Number(q.price)) && Number(q.price)>0;
        }).length;
        // Some older/degraded Workers answer /quotes but fail almost everything while /quote still works.
        if (chunk.length >= 4 && successes <= Math.max(1, Math.floor(chunk.length * 0.1))) {
          quoteWorkerMode = "single";
          Object.assign(out, await fetchQuotesIndividually(chunk, 5));
        } else {
          Object.assign(out, batch);
        }
      } catch (e) {
        quoteWorkerMode = "single";
        Object.assign(out, await fetchQuotesIndividually(chunk, 5));
      }
    }
  });
  await Promise.all(workers);
  return out;
}
'''
assert old in s, 'batch block anchor missing'
s=s.replace(old,new,1)
s=s.replace('  let updated = 0, failed = 0;\n  const errors = [];','  let updated = 0, failed = 0, skipped = 0;\n  const errors = [];\n  quoteWorkerMode = "batch";',1)
old_no='''  noCandidateRefs.forEach(ref => {
    const rawUp = String(ref.raw || "").toUpperCase().trim();
    const baseUp = canonicalBrokerTickerBase(rawUp);
    if (SKIP_TICKERS.has(rawUp) || SKIP_TICKERS.has(baseUp)) return;
    failed++;
    errors.push({
      raw: ref.raw, yahoo: "", assetName: ref.asset.name || ref.raw || "Ativo",
      reason: "Sem ticker Yahoo reconhecível para este ativo"
    });
  });'''
new_no='''  noCandidateRefs.forEach(ref => {
    const rawUp = String(ref.raw || "").toUpperCase().trim();
    const baseUp = canonicalBrokerTickerBase(rawUp);
    if (SKIP_TICKERS.has(rawUp) || SKIP_TICKERS.has(baseUp)) { skipped++; return; }
    // Missing/unsafe identity is not a network failure. Keep the last value and report as skipped.
    skipped++;
  });'''
assert old_no in s
s=s.replace(old_no,new_no,1)
s=s.replace('state.settings.lastQuoteRefresh = { updated, failed, errors, ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };','state.settings.lastQuoteRefresh = { updated, failed, skipped, errors, workerMode:quoteWorkerMode, ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };',1)
# improve status metadata
old_meta='''    meta.textContent = `${report.updated || 0} atualizadas · ${report.failed} com erro${secs}`;'''
new_meta='''    const skipped = report.skipped ? ` · ${report.skipped} ignoradas` : "";
    const mode = report.workerMode === "single" ? " · compatibilidade" : "";
    meta.textContent = `${report.updated || 0} atualizadas · ${report.failed} com erro${skipped}${mode}${secs}`;'''
s=s.replace(old_meta,new_meta,1)
old_ok='''    meta.textContent = `${report.updated} atualizadas${secs} · automático`;'''
new_ok='''    const skipped = report.skipped ? ` · ${report.skipped} ignoradas` : "";
    const mode = report.workerMode === "single" ? " · compatibilidade" : "";
    meta.textContent = `${report.updated} atualizadas${skipped}${mode}${secs} · automático`;'''
s=s.replace(old_ok,new_ok,1)
s=s.replace('sw.js?v=20260509v66','sw.js?v=20260509v67')
p.write_text(s)

p=root/'README.md'; r=p.read_text()
if not r.startswith('## Vestra v6.6.4'):
    r='''## Vestra v6.6.4 — Quote Refresh Compatibility & Diagnostics\n\n- O refresh deteta automaticamente um Worker sem `/quotes` compatível e faz fallback para `/quote` individual com concorrência limitada.\n- Se o endpoint batch responder mas falhar quase todo o lote, a app também muda automaticamente para o modo de compatibilidade.\n- Ativos sem identidade segura deixam de ser apresentados como erros de rede: são contados como ignorados e mantêm o último valor conhecido.\n- O estado da sincronização mostra quando foi usado modo de compatibilidade.\n- Manual e automático usam exatamente o mesmo caminho.\n- PWA cache: `vestra-cache-v67`.\n\n'''+r
p.write_text(r)
p=root/'sw.js'; sw=p.read_text().replace('vestra-cache-v66','vestra-cache-v67'); p.write_text(sw)
