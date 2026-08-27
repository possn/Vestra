/* Vestra Market Client v1.0 — Worker quote transport, FX fallback and bounded concurrency. */
(() => {
  'use strict';

  const FX_FALLBACK_LOCAL = Object.freeze({
    USD:0.92, GBP:1.17, DKK:0.134, CHF:1.05, PLN:0.23,
    SEK:0.087, NOK:0.085, CAD:0.68, AUD:0.59, JPY:0.006, HKD:0.118
  });

  async function fetchQuote(ticker, workerUrl, timeoutMs=10000) {
    const base=String(workerUrl||'').replace(/\/$/,'');
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
        const q=await fetchQuote(`EUR${ccy}=X`,workerUrl);
        if(q&&Number(q.price)>0)rates[ccy]=1/Number(q.price);
      } catch(_) {}
    }));
    for(const ccy of ccys)if(!rates[ccy])rates[ccy]=Number(fallbacks?.[ccy])||1;
    return rates;
  }

  window.VestraMarketClient=Object.freeze({
    version:'1.0',
    FX_FALLBACK_LOCAL,
    fetchQuote,
    fetchFxRates,
    mapWithConcurrency,
  });
})();
