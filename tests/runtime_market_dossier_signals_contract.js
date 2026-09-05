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

// Startup rows deliberately omit full provenance; evidence appears only after dossier hydration.
assert.equal(api.evidencePanel({ticker:'ABC',confidence_score:68}),'');
assert.equal(api.catalystPanel({}),'');

const evidence=api.evidencePanel({
  ticker:'ABC',score:77,confidence_score:68.4,data_coverage_pct:84.7,fundamental_age_days:420,
  confidence_reasons:['Cobertura fundamental elevada','Dependência <single-source>'],
  data_provenance:{
    evidence_state:'carried_forward',
    independent_fundamental_source_count:1,
    independent_fundamental_source_families:['yahoo'],
  },
});
assert(evidence.includes('QUALIDADE DA EVIDÊNCIA'));
assert(evidence.includes('Yahoo'));
assert(evidence.includes('Transportado do último build válido'));
assert(evidence.includes('1 fonte'));
assert(evidence.includes('68/100'));
assert(evidence.includes('85%'));
assert(evidence.includes('420 dias · atenção'));
assert(evidence.includes('Dependência &lt;single-source&gt;'));
assert(evidence.includes('Analyst, insiders e divulgações políticas'));
assert(evidence.includes('não altera o Score Vestra'));
assert(!evidence.includes('77/100'));
assert(!evidence.includes('Acordo entre fontes ·'));

const measuredAgreement=api.evidencePanel({
  confidence_score:91,data_coverage_pct:92,
  data_provenance:{
    evidence_state:'observed',
    independent_fundamental_source_count:2,
    independent_fundamental_source_families:['yahoo','esef'],
    agreement_checks:4,
    agreement_pct:75,
    agreement_period_end:'2025-12-31',
  },
});
assert(measuredAgreement.includes('Yahoo + ESEF'));
assert(measuredAgreement.includes('Acordo entre fontes · 75%'));
assert(measuredAgreement.includes('4 métricas anuais do mesmo exercício'));
assert(measuredAgreement.includes('DATE:2025-12-31'));
assert(measuredAgreement.includes('is-warn'));
assert(measuredAgreement.includes('compara apenas métricas anuais do mesmo exercício'));

const oneMetricAgreement=api.evidencePanel({
  data_provenance:{
    evidence_state:'observed',
    independent_fundamental_source_count:2,
    independent_fundamental_source_families:['yahoo','esef'],
    agreement_checks:1,
    agreement_pct:100,
    agreement_period_end:'2025-12-31',
  },
});
assert(!oneMetricAgreement.includes('Acordo entre fontes ·'));

const strongAgreement=api.evidencePanel({
  data_provenance:{evidence_state:'observed',independent_fundamental_source_count:2,independent_fundamental_source_families:['yahoo','esef'],agreement_checks:3,agreement_pct:100},
});
assert(strongAgreement.includes('is-positive'));

const weakAgreement=api.evidencePanel({
  data_provenance:{evidence_state:'observed',independent_fundamental_source_count:2,independent_fundamental_source_families:['yahoo','esef'],agreement_checks:3,agreement_pct:66.7},
});
assert(weakAgreement.includes('is-risk'));

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

const catalystWithEvidence=api.catalystPanel({
  data_provenance:{evidence_state:'observed',independent_fundamental_source_count:2,independent_fundamental_source_families:['yahoo','sec_edgar']},
  confidence_score:91,data_coverage_pct:92,
  catalyst_events:[{tone:'event',label:'Resultados',date:'2026-10-01'}],
});
assert(catalystWithEvidence.indexOf('QUALIDADE DA EVIDÊNCIA') < catalystWithEvidence.indexOf('CATALYSTS & RISKS'));
assert(catalystWithEvidence.includes('Yahoo + SEC EDGAR'));
assert(catalystWithEvidence.includes('Observado no build atual'));

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
