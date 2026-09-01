const fs=require('fs');
const vm=require('vm');
const assert=require('assert');

const context={window:{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('market-dossier-signals.js','utf8'),context,{filename:'market-dossier-signals.js'});

assert.equal(context.window.VestraMarketDossierSignals?.version,'1.0');
assert.equal(typeof context.window.VestraMarketDossierSignals?.create,'function');

const txt=v=>String(v??'').trim();
const n=v=>{ if(v===null||v===undefined||v==='') return null; const x=Number(v); return Number.isFinite(x)?x:null; };
const esc=v=>txt(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api=context.window.VestraMarketDossierSignals.create({text:txt,number:n,escapeHtml:esc,formatShortDate:v=>`DATE:${v}`});

assert.equal(api.catalystPanel({}),'');
const catalyst=api.catalystPanel({
  catalyst_summary:'Roadmap <strong>',
  catalyst_next_date:'2026-10-01',
  catalyst_events:[
    {tone:'positive',label:'Resultados <Q3>',date:'2026-10-01',evidence:'EPS & vendas',source:'IR'},
    {tone:'risk',label:'Risco',window:'2H 2026'},
  ],
});
assert(catalyst.includes('CATALYSTS & RISKS'));
assert(catalyst.includes('Próximo · DATE:2026-10-01'));
assert(catalyst.includes('market-change-item--up'));
assert(catalyst.includes('market-change-item--down'));
assert(catalyst.includes('Roadmap &lt;strong&gt;'));
assert(catalyst.includes('Resultados &lt;Q3&gt;'));
assert(!catalyst.includes('Roadmap <strong>'));

assert.equal(api.recoveryPanel({recovery_status:'insufficient'}),'');
const recovery=api.recoveryPanel({
  recovery_status:'confirmed',recovery_label:'Confirmada',recovery_score:81.6,
  recovery_return_20d_pct:5.25,recovery_return_60d_pct:-2.04,
  recovery_price_score:75,recovery_fundamental_score:88,
  recovery_reasons:['Margens <melhoram>','FCF forte'],
});
assert(recovery.includes('RECOVERY CONFIRMATION'));
assert(recovery.includes('is-positive'));
assert(recovery.includes('82/100'));
assert(recovery.includes('+5.3%'));
assert(recovery.includes('-2.0%'));
assert(recovery.includes('Margens &lt;melhoram&gt;'));
assert(recovery.includes('nem altera o Score Vestra'));

assert.equal(api.drawdownPanel({drawdown_diagnosis_status:'not_material',drawdown_diagnosis:[{}]}),'');
const drawdown=api.drawdownPanel({
  drawdown_diagnosis_status:'mixed',drawdown_from_high_pct:-31.7,
  sector_relative_drawdown_label:'Melhor que peers',sector_relative_return_1y_pct:4.25,sector_relative_peer_count:8,
  drawdown_diagnosis:[
    {label:'Revisões <EPS>',strength:82,trend:'improving',evidence:['EPS estabiliza','Guidance & mix']},
    {label:'Macro',strength:55,trend:'deteriorating',evidence:['Taxas']},
  ],
});
assert(drawdown.includes('Queda com causas mistas'));
assert(drawdown.includes('-32% vs máximo 52s'));
assert(drawdown.includes('+4.3 pp vs mediana do setor · 8 pares'));
assert(drawdown.includes('Revisões &lt;EPS&gt;'));
assert(drawdown.includes('is-primary'));
assert(drawdown.includes('is-positive'));
assert(drawdown.includes('is-risk'));
assert(drawdown.includes('não prova causalidade'));

console.log('market dossier signals runtime contract: ok');
