/* Lightweight canonical five-axis fundamental radar model. */
(() => {
  'use strict';
  const n=v=>v===null||v===undefined||v===''?null:(Number.isFinite(Number(v))?Number(v):null);
  function dossierRadarClamp(value){
    const v=n(value);
    return v==null?null:Math.max(0,Math.min(100,v));
  }

  function dossierRadarBlend(rows){
    let total=0, weight=0, observed=false;
    for(const [raw,w] of rows){
      const value=dossierRadarClamp(raw);
      const ww=Number.isFinite(Number(w))?Number(w):0;
      if(ww<=0) continue;
      total+=(value==null?50:value)*ww;
      weight+=ww;
      if(value!=null) observed=true;
    }
    return observed&&weight>0?Math.max(0,Math.min(100,total/weight)):null;
  }

  function dossierDividendRadar(s){
    const rawYield=n(s?.dividend_yield);
    if(rawYield==null||rawYield<=0) return null;
    const yieldPct=Math.abs(rawYield)<=1?rawYield*100:rawYield;
    const sectorRaw=n(s?.sector_dividend_yield_median);
    const sectorYield=sectorRaw==null?null:(Math.abs(sectorRaw)<=1?sectorRaw*100:sectorRaw);
    const yieldScore=sectorYield!=null&&sectorYield>0
      ? Math.max(0,Math.min(100,50*(yieldPct/sectorYield)))
      : Math.max(0,Math.min(100,(yieldPct/4)*100));

    const rawPayout=n(s?.payout_ratio);
    const payout=rawPayout==null?null:(Math.abs(rawPayout)<=1?rawPayout*100:rawPayout);
    let payoutScore=null;
    if(payout!=null){
      if(payout<=0) payoutScore=50;
      else if(payout<25) payoutScore=60+(payout/25)*20;
      else if(payout<=70) payoutScore=90;
      else if(payout<=100) payoutScore=90-((payout-70)/30)*60;
      else payoutScore=Math.max(0,30-(payout-100));
    }

    const coverage=n(s?.dividend_fcf_coverage);
    let coverageScore=null;
    if(coverage!=null){
      if(coverage>=2) coverageScore=100;
      else if(coverage>=1) coverageScore=60+(coverage-1)*40;
      else if(coverage>=0) coverageScore=20+coverage*40;
      else coverageScore=0;
    }
    return dossierRadarBlend([[yieldScore,.35],[payoutScore,.30],[coverageScore,.35]]);
  }

  function dossierRadarAxes(s){
    return [
      {key:'value',label:'Valor',value:dossierRadarClamp(s?.value_pct),detail:'Valuation relativo do modelo Vestra.'},
      {key:'future',label:'Futuro',value:dossierRadarBlend([[s?.growth_pct,.65],[s?.estimate_momentum_score,.35]]),detail:'Growth e direção das estimativas.'},
      {key:'past',label:'Histórico',value:dossierRadarBlend([[s?.quality_pct,.45],[s?.stability_pct,.30],[s?.execution_pct,.25]]),detail:'Qualidade, estabilidade e execução observada.'},
      {key:'health',label:'Saúde',value:dossierRadarBlend([[s?.balance_pct,.40],[s?.cashflow_pct,.35],[s?.earnings_quality_pct,.25]]),detail:'Balanço, cash flow e qualidade dos lucros.'},
      {key:'dividend',label:'Dividendo',value:dossierDividendRadar(s),detail:'Yield contextualizado e sustentabilidade por payout/FCF.'},
    ];
  }

  window.VestraDossierRadarAxes = dossierRadarAxes;
})();
