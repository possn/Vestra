/* Vestra Market Client v1.3 — iOS-safe quote coalescing, Worker batch GET and bounded fallback. */
(() => {
  'use strict';

  const FX_FALLBACK_LOCAL = Object.freeze({
    USD:0.92, GBP:1.17, DKK:0.134, CHF:1.05, PLN:0.23,
    SEK:0.087, NOK:0.085, CAD:0.68, AUD:0.59, JPY:0.006, HKD:0.118
  });

  // app.js asks for 8 workers, but the transport keeps the proven iOS ceiling.
  // fetchQuote calls inside those workers are coalesced into one /quotes GET, so
  // four portfolio rows normally consume one browser connection instead of four.
  const MAX_QUOTE_CONCURRENCY = 4;
  const DEFAULT_QUOTE_TIMEOUT_MS = 12000;
  const BATCH_QUOTE_TIMEOUT_MS = 18000;
  const BATCH_WINDOW_MS = 12;
  const BATCH_CHUNK_SIZE = 4;
  const DIRECT_FALLBACK_CONCURRENCY = 2;

  const cleanWorkerUrl = workerUrl => String(workerUrl||'').replace(/\/$/,'');
  const batchSupport = new Map(); // worker base -> true/false once learned

  function isTimeoutError(err) {
    const name=String(err?.name||'');
    const msg=String(err?.message||'');
    return name==='AbortError' || name==='TimeoutError' || /aborted|timeout|timed out|tempo limite/i.test(msg);
  }

  async function fetchWithTimeout(url, options={}, timeoutMs=DEFAULT_QUOTE_TIMEOUT_MS) {
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(), Math.max(1000, Number(timeoutMs)||DEFAULT_QUOTE_TIMEOUT_MS));
    try {
      return await fetch(url,{...options,signal:controller.signal});
    } finally {
      clearTimeout(timer);
    }
  }

  async function fetchQuoteDirect(ticker, workerUrl, timeoutMs=DEFAULT_QUOTE_TIMEOUT_MS) {
    const base=cleanWorkerUrl(workerUrl);
    if(!base) throw new Error('Worker URL não configurado');
    const url=`${base}/quote?ticker=${encodeURIComponent(String(ticker||'').trim())}`;
    let resp;
    try {
      resp=await fetchWithTimeout(url,{},timeoutMs);
    } catch(e) {
      if(isTimeoutError(e)) throw new Error(`Tempo limite do Worker (${Math.round(timeoutMs/1000)}s)`);
      throw new Error(`Worker inacessível: ${e?.message||'erro de rede'}`);
    }
    let data=null;
    try { data=await resp.clone().json(); } catch(_) {}
    if(!resp.ok){
      const detail=data?.error?`: ${data.error}`:'';
      throw new Error(`Worker HTTP ${resp.status}${detail}`);
    }
    if(data?.error) throw new Error(data.error);
    return data;
  }

  async function fetchQuotesBatch(tickers, workerUrl, timeoutMs=BATCH_QUOTE_TIMEOUT_MS) {
    const base=cleanWorkerUrl(workerUrl);
    if(!base) throw new Error('Worker URL não configurado');
    const unique=[...new Set((tickers||[]).map(x=>String(x||'').trim().toUpperCase()).filter(Boolean))];
    const quotes={};
    const errors={};
    let unsupported=batchSupport.get(base)===false;
    if(unsupported) return {quotes,errors,unsupported:true};

    // Worker v4.2 exposes GET /quotes?tickers=... and caps at 20. Keep client
    // chunks deliberately small: the Worker resolves the symbols in parallel and
    // Safari only has to keep one HTTP request alive for the group.
    for(let i=0;i<unique.length;i+=BATCH_CHUNK_SIZE){
      const chunk=unique.slice(i,i+BATCH_CHUNK_SIZE);
      const qs=chunk.map(encodeURIComponent).join(',');
      let resp;
      try {
        resp=await fetchWithTimeout(`${base}/quotes?tickers=${qs}`,{
          method:'GET', headers:{'Accept':'application/json'}
        },timeoutMs);
      } catch(e) {
        const msg=isTimeoutError(e)
          ? `Tempo limite do Worker (${Math.round(timeoutMs/1000)}s)`
          : `Worker inacessível: ${e?.message||'erro de rede'}`;
        chunk.forEach(t=>{ errors[t]=msg; });
        continue;
      }

      let data=null;
      try { data=await resp.clone().json(); } catch(_) {}
      if([404,405,501].includes(resp.status)){
        unsupported=true;
        batchSupport.set(base,false);
        break;
      }
      if(!resp.ok){
        const msg=`Worker HTTP ${resp.status}${data?.error?`: ${data.error}`:''}`;
        chunk.forEach(t=>{ errors[t]=msg; });
        continue;
      }

      batchSupport.set(base,true);
      for(const t of chunk){
        const row=data && data[t];
        if(row && !row.error && Number(row.price)>0) quotes[t]=row;
        else errors[t]=row?.error || 'Sem cotação disponível';
      }
    }
    return {quotes,errors,unsupported};
  }

  // A tiny queue lets existing app.js code keep calling fetchQuote(ticker)
  // without knowing about batching. Calls arriving in the same render/refresh
  // wave are grouped by Worker URL and resolved through /quotes.
  const pendingByBase=new Map();
  let batchTimer=null;

  function queueQuote(ticker, workerUrl, timeoutMs){
    const base=cleanWorkerUrl(workerUrl);
    const tk=String(ticker||'').trim().toUpperCase();
    return new Promise((resolve,reject)=>{
      if(!base) { reject(new Error('Worker URL não configurado')); return; }
      if(!tk) { reject(new Error('Ticker vazio')); return; }
      if(!pendingByBase.has(base)) pendingByBase.set(base,[]);
      pendingByBase.get(base).push({ticker:tk,timeoutMs,resolve,reject});
      if(!batchTimer) batchTimer=setTimeout(flushQuoteQueue,BATCH_WINDOW_MS);
    });
  }

  async function runDirectFallback(entries, base){
    let cursor=0;
    const workers=Array.from({length:Math.min(DIRECT_FALLBACK_CONCURRENCY,entries.length||1)},async()=>{
      while(true){
        const idx=cursor++;
        if(idx>=entries.length) return;
        const e=entries[idx];
        try { e.resolve(await fetchQuoteDirect(e.ticker,base,e.timeoutMs||DEFAULT_QUOTE_TIMEOUT_MS)); }
        catch(err){ e.reject(err); }
      }
    });
    await Promise.all(workers);
  }

  async function flushQuoteQueue(){
    batchTimer=null;
    const groups=[...pendingByBase.entries()];
    pendingByBase.clear();

    await Promise.all(groups.map(async([base,entries])=>{
      if(batchSupport.get(base)===false){
        await runDirectFallback(entries,base);
        return;
      }

      // Resolve duplicates once but fan the result out to every caller.
      const tickers=[...new Set(entries.map(e=>e.ticker))];
      const timeout=Math.max(BATCH_QUOTE_TIMEOUT_MS,...entries.map(e=>Number(e.timeoutMs)||0));
      const result=await fetchQuotesBatch(tickers,base,timeout);
      if(result.unsupported){
        await runDirectFallback(entries,base);
        return;
      }

      for(const e of entries){
        const q=result.quotes[e.ticker];
        if(q){ e.resolve(q); continue; }
        e.reject(new Error(result.errors[e.ticker] || 'Sem cotação disponível'));
      }
    }));
  }

  async function fetchQuote(ticker, workerUrl, timeoutMs=DEFAULT_QUOTE_TIMEOUT_MS) {
    return queueQuote(ticker,workerUrl,timeoutMs);
  }

  async function mapWithConcurrency(items, concurrency, fn) {
    const list=Array.isArray(items)?items:[];
    const requested=Math.max(1,Number(concurrency)||1);
    const effective=Math.min(requested,MAX_QUOTE_CONCURRENCY,list.length||1);
    const out=new Array(list.length);
    let cursor=0;
    const workers=Array.from({length:effective},async()=>{
      while(true){
        const idx=cursor++;
        if(idx>=list.length)return;
        try { out[idx]={status:'fulfilled',value:await fn(list[idx],idx)}; }
        catch(reason){ out[idx]={status:'rejected',reason}; }
      }
    });
    await Promise.all(workers);
    return out;
  }

  async function fetchFxRates(currencies, workerUrl, fallbacks=FX_FALLBACK_LOCAL) {
    const ccys=[...new Set([...(currencies||[])].map(x=>String(x||'').trim().toUpperCase()).filter(x=>x&&x!=='EUR'))];
    const rates={};
    // These calls are also coalesced, so a portfolio with many currencies no
    // longer opens a burst of independent Worker connections on foregrounding.
    await Promise.allSettled(ccys.map(async ccy=>{
      try {
        const q=await fetchQuote(`EUR${ccy}=X`,workerUrl,10000);
        if(q&&Number(q.price)>0)rates[ccy]=1/Number(q.price);
      } catch(_) {}
    }));
    for(const ccy of ccys)if(!rates[ccy])rates[ccy]=Number(fallbacks?.[ccy])||1;
    return rates;
  }

  window.VestraMarketClient=Object.freeze({
    version:'1.3',
    FX_FALLBACK_LOCAL,
    MAX_QUOTE_CONCURRENCY,
    DEFAULT_QUOTE_TIMEOUT_MS,
    BATCH_QUOTE_TIMEOUT_MS,
    cleanWorkerUrl,
    fetchQuote,
    fetchQuotesBatch,
    fetchFxRates,
    mapWithConcurrency,
  });
})();
