/* Vestra Market Client v1.5 — identity-safe batching, quote dedupe and FX caching. */
(() => {
  'use strict';

  const FX_FALLBACK_LOCAL = Object.freeze({
    USD:0.92, GBP:1.17, DKK:0.134, CHF:1.05, PLN:0.23,
    SEK:0.087, NOK:0.085, CAD:0.68, AUD:0.59, JPY:0.006, HKD:0.118
  });

  // Portfolio refresh uses high logical concurrency only to enqueue work. Actual
  // browser->Worker traffic remains bounded and batched below.
  const MAX_QUOTE_CONCURRENCY = 600;
  const DEFAULT_QUOTE_TIMEOUT_MS = 12000;
  const BATCH_QUOTE_TIMEOUT_MS = 12000;
  const BATCH_WINDOW_MS = 24;
  const BATCH_CHUNK_SIZE = 20;
  const BATCH_REQUEST_CONCURRENCY = 8;
  const DIRECT_FALLBACK_CONCURRENCY = 2;
  const QUOTE_CACHE_TTL_MS = 60 * 1000;
  const QUOTE_ERROR_TTL_MS = 20 * 1000;
  const FX_CACHE_TTL_MS = 4 * 60 * 60 * 1000;

  const cleanWorkerUrl = workerUrl => String(workerUrl||'').replace(/\/$/,'');
  const batchSupport = new Map();
  const quoteCache = new Map();
  const quoteErrorCache = new Map();
  const quoteInflight = new Map();
  const fxCache = new Map();

  function isTimeoutError(err) {
    const name=String(err?.name||'');
    const msg=String(err?.message||'');
    return name==='AbortError' || name==='TimeoutError' || /aborted|timeout|timed out|tempo limite/i.test(msg);
  }

  function freshEntry(map,key,ttl){
    const row=map.get(key);
    if(!row) return null;
    if(Date.now()-Number(row.ts||0)>ttl){ map.delete(key); return null; }
    return row;
  }

  async function fetchWithTimeout(url, options={}, timeoutMs=DEFAULT_QUOTE_TIMEOUT_MS) {
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(), Math.max(1000, Number(timeoutMs)||DEFAULT_QUOTE_TIMEOUT_MS));
    try { return await fetch(url,{...options,signal:controller.signal}); }
    finally { clearTimeout(timer); }
  }

  async function fetchQuoteDirect(ticker, workerUrl, timeoutMs=DEFAULT_QUOTE_TIMEOUT_MS) {
    const base=cleanWorkerUrl(workerUrl);
    if(!base) throw new Error('Worker URL não configurado');
    const url=`${base}/quote?ticker=${encodeURIComponent(String(ticker||'').trim())}`;
    let resp;
    try { resp=await fetchWithTimeout(url,{},timeoutMs); }
    catch(e) {
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

    const chunks=[];
    for(let i=0;i<unique.length;i+=BATCH_CHUNK_SIZE) chunks.push(unique.slice(i,i+BATCH_CHUNK_SIZE));
    let cursor=0;
    const workerCount=Math.min(BATCH_REQUEST_CONCURRENCY,chunks.length||1);

    const workers=Array.from({length:workerCount},async()=>{
      while(true){
        const idx=cursor++;
        if(idx>=chunks.length || unsupported) return;
        const chunk=chunks[idx];
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
          return;
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
    });
    await Promise.all(workers);
    return {quotes,errors,unsupported};
  }

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
    const base=cleanWorkerUrl(workerUrl);
    const tk=String(ticker||'').trim().toUpperCase();
    if(!base) throw new Error('Worker URL não configurado');
    if(!tk) throw new Error('Ticker vazio');
    const key=`${base}|${tk}`;

    const cached=freshEntry(quoteCache,key,QUOTE_CACHE_TTL_MS);
    if(cached) return cached.value;
    const cachedErr=freshEntry(quoteErrorCache,key,QUOTE_ERROR_TTL_MS);
    if(cachedErr) throw cachedErr.error;
    if(quoteInflight.has(key)) return quoteInflight.get(key);

    const task=queueQuote(tk,base,timeoutMs)
      .then(value=>{
        quoteCache.set(key,{ts:Date.now(),value});
        quoteErrorCache.delete(key);
        return value;
      })
      .catch(err=>{
        const error=err instanceof Error?err:new Error(String(err||'Erro ao obter cotação'));
        quoteErrorCache.set(key,{ts:Date.now(),error});
        throw error;
      })
      .finally(()=>quoteInflight.delete(key));
    quoteInflight.set(key,task);
    return task;
  }

  async function mapWithConcurrency(items, concurrency, fn) {
    const list=Array.isArray(items)?items:[];
    const requested=Math.max(1,Number(concurrency)||1);
    // Large portfolio refreshes must enqueue together so queueQuote can coalesce
    // them into true Worker batches. Small generic maps keep the requested limit.
    const promoted=list.length>=40 ? Math.min(list.length,MAX_QUOTE_CONCURRENCY) : requested;
    const effective=Math.min(promoted,MAX_QUOTE_CONCURRENCY,list.length||1);
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
    const base=cleanWorkerUrl(workerUrl);
    const ccys=[...new Set([...(currencies||[])].map(x=>String(x||'').trim().toUpperCase()).filter(x=>x&&x!=='EUR'))];
    const rates={};
    const missing=[];

    for(const ccy of ccys){
      const row=freshEntry(fxCache,`${base}|${ccy}`,FX_CACHE_TTL_MS);
      if(row && Number(row.rate)>0) rates[ccy]=Number(row.rate);
      else missing.push(ccy);
    }

    await Promise.allSettled(missing.map(async ccy=>{
      try {
        const q=await fetchQuote(`EUR${ccy}=X`,base,10000);
        if(q&&Number(q.price)>0){
          const rate=1/Number(q.price);
          rates[ccy]=rate;
          fxCache.set(`${base}|${ccy}`,{ts:Date.now(),rate});
        }
      } catch(_) {}
    }));

    for(const ccy of ccys)if(!rates[ccy])rates[ccy]=Number(fallbacks?.[ccy])||1;
    return rates;
  }

  window.VestraMarketClient=Object.freeze({
    version:'1.5',
    FX_FALLBACK_LOCAL,
    MAX_QUOTE_CONCURRENCY,
    DEFAULT_QUOTE_TIMEOUT_MS,
    BATCH_QUOTE_TIMEOUT_MS,
    BATCH_CHUNK_SIZE,
    BATCH_REQUEST_CONCURRENCY,
    cleanWorkerUrl,
    fetchQuote,
    fetchQuotesBatch,
    fetchFxRates,
    mapWithConcurrency,
  });
})();
