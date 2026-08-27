/* Vestra Quote Errors v1.0 — classify quote refresh failures for actionable diagnostics. */
(() => {
  'use strict';

  const RULES = [
    { key:'no_data', label:'Sem dados Yahoo', re:/sem dados|não foi possível obter uma cotação válida|no data|not found|404/i },
    { key:'identity', label:'Ticker / identidade', re:/ticker|isin|identidade|correspondência errada|sem ticker/i },
    { key:'delisted', label:'Delisted / ignorado', re:/delist|privat|acquired|merger|ignorado|skip/i },
    { key:'network', label:'Rede / Worker', re:/worker|timeout|http\s*5\d\d|inacessível|network|fetch/i },
    { key:'sanity', label:'Sanity de preço', re:/cotação suspeita|moeda .* não coincide|último preço fiável|cotação inválida/i },
  ];

  function classifyQuoteError(err) {
    const reason=String((err&&err.reason)||err||'').trim();
    for(const r of RULES) if(r.re.test(reason)) return { key:r.key, label:r.label };
    return { key:'other', label:'Outro' };
  }

  function summarizeQuoteErrors(errors) {
    const counts=new Map();
    for(const err of (Array.isArray(errors)?errors:[])) {
      const c=classifyQuoteError(err);
      const cur=counts.get(c.key)||{key:c.key,label:c.label,count:0};
      cur.count++;
      counts.set(c.key,cur);
    }
    return [...counts.values()].sort((a,b)=>b.count-a.count || a.label.localeCompare(b.label));
  }

  function decorateQuoteError(err) {
    const base=(err&&typeof err==='object')?{...err}:{reason:String(err||'')};
    const c=classifyQuoteError(base);
    return {...base, category:c.key, categoryLabel:c.label};
  }

  window.VestraQuoteErrors=Object.freeze({ version:'1.0', classifyQuoteError, summarizeQuoteErrors, decorateQuoteError });
})();
