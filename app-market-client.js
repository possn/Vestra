/* Vestra Market Client v1.1 — Worker batch quote transport, FX fallback and bounded concurrency. */
(() => {
  'use strict';

  const FX_FALLBACK_LOCAL = Object.freeze({
    USD:0.92, GBP:1.17, DKK:0.134, CHF:1.05, PLN:0.23,
    SEK:0.087, NOK:0.085, CAD:0.68, AUD:0.59, JPY:0.006, HKD:0.118
  });

  const cleanWorkerUrl = workerUrl => String(workerUrl||'').replace(/\/$/,'');

  async function fetchQuote(ticker, workerUrl, timeoutMs=7000) {
    const base=cleanWorkerUrl(workerUrl);
    if(!base) throw new Error('Worker URL não configurado');
    const url=`${base}/quote?ticker=${encodeURIComponent(String(ticker||'').trim())}`;
    let resp;
    try {
      resp=await fetch(url,{signal:AbortSignal.timeout(timeoutMs)});
    } catch(e) {
      throw new Error(`Worker inacessível: ${e?.message||'timeout'}`);
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

  async function fetchQuotesBatch(tickers, workerUrl, timeoutMs=9000) {
    const base=cleanWorkerUrl(workerUrl);
    if(!base) throw new Error('Worker URL não configurado');
    const unique=[...new Set((tickers||[]).map(x=>String(x||'').trim().toUpperCase()).filter(Boolean))];
    const quotes={};
    const errors={};
    let unsupported=false;

    for(let i=0;i<unique.length;i+=80){
      const chunk=unique.slice(i,i+80);
      let lastErr=null;
      let done=false;
      for(let attempt=0;attempt<2 && !done;attempt++){
        try {
          const resp=await fetch(`${base}/quotes`,{
            method:'POST',
            headers:{'Content-Type':'application/json','Accept':'application/json'},
            body:JSON.stringify({tickers:chunk}),
            signal:AbortSignal.timeout(timeoutMs)
          });
          let data=null;
          try { data=await resp.clone().json(); } catch(_) {}
          if([404,405,501].includes(resp.status)){
            unsupported=true;
            throw new Error(`Worker HTTP ${resp.status}`);
          }
          if(!resp.ok) throw new Error(`Worker HTTP ${resp.status}${data?.error?`: ${data.error}`:''}`);
          Object.assign(quotes,data?.quotes||{});
          Object.assign(errors,data?.errors||{});
          done=true;
        } catch(e) {
          lastErr=e;
          if(unsupported) break;
          if(attempt===0) await new Promise(r=>setTimeout(r,300));
        }
      }
      if(!done){
        const msg=`Worker inacessível: ${lastErr?.message||'timeout'}`;
        chunk.forEach(t=>{ if(!quotes[t]&&!errors[t]) errors[t]=msg; });
        if(unsupported) break;
      }
    }
    return {quotes,errors,unsupported};
  }

  async function mapWithConcurrency(items, concurrency, fn) {
    const list=Array.isArray(items)?items:[];
    const out=new Array(list.length);
    let cursor=0;
    const workers=Array.from({length:Math.max(1,Math.min(Number(concurrency)||1,list.length||1))},async()=>{
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
    await Promise.allSettled(ccys.map(async ccy=>{
      try {
        const q=await fetchQuote(`EUR${ccy}=X`,workerUrl,5000);
        if(q&&Number(q.price)>0)rates[ccy]=1/Number(q.price);
      } catch(_) {}
    }));
    for(const ccy of ccys)if(!rates[ccy])rates[ccy]=Number(fallbacks?.[ccy])||1;
    return rates;
  }

  window.VestraMarketClient=Object.freeze({
    version:'1.1',
    FX_FALLBACK_LOCAL,
    cleanWorkerUrl,
    fetchQuote,
    fetchQuotesBatch,
    fetchFxRates,
    mapWithConcurrency,
  });
})();
