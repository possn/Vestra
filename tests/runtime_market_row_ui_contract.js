const fs=require('fs');
const vm=require('vm');
const assert=require('assert');

const context={window:{},Intl,Date,Number,Math};
vm.createContext(context);
vm.runInContext(fs.readFileSync('market-row-ui.js','utf8'),context,{filename:'market-row-ui.js'});
assert.equal(context.window.VestraMarketRowUI?.version,'1.0');

const txt=v=>String(v??'').trim();
const n=v=>{ if(v===null||v===undefined||v==='') return null; const x=Number(v); return Number.isFinite(x)?x:null; };
const esc=v=>txt(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const held=new Set(['MSFT']);
const watched=new Set(['VWCE.DE']);
const api=context.window.VestraMarketRowUI.create({
  text:txt,
  number:n,
  escapeHtml:esc,
  getGeneratedAt:()=> '2026-09-01T06:00:00Z',
  inPortfolio:t=>held.has(t),
  isWatched:t=>watched.has(t),
  changeBadge:s=>`<span class="changed">${esc(s.ticker)}</span>`,
});

assert.equal(api.isFund({quote_type:'ETF',name:'Whatever'}),true);
assert.equal(api.isFund({quote_type:'MUTUALFUND',name:'Whatever'}),true);
assert.equal(api.isFund({name:'iShares Core MSCI World'}),true);
assert.equal(api.isFund({quote_type:'EQUITY',name:'Microsoft Corporation'}),false);

assert.equal(api.scoreClass(null),'market-score--soft');
assert.equal(api.scoreClass(71),'');
assert.equal(api.scoreClass(60),'market-score--soft');
assert.equal(api.scoreClass(40),'market-score--risk');
assert(api.ageText().startsWith('Dados '));

const heldHtml=api.renderRow({ticker:'MSFT',name:'Microsoft <Corp>',sector:'Technology',score:82});
assert(heldHtml.includes('Carteira'));
assert(heldHtml.includes('Microsoft &lt;Corp&gt;'));
assert(heldHtml.includes('data-market-watch="MSFT"'));
assert(heldHtml.includes('☆'));
assert(heldHtml.includes('class="changed"'));
assert(heldHtml.includes('>82<'));

const watchedHtml=api.renderRow({ticker:'VWCE.DE',name:'Vanguard FTSE All-World UCITS ETF',sector:'ETF',score:77});
assert(watchedHtml.includes('★'));
assert(watchedHtml.includes('is-active'));
assert(watchedHtml.includes('class="changed"'));

const displayScoreHtml=api.renderRow({ticker:'ABC',name:'ABC',sector:'Industrials',score:10},'Opportunity 88/100',88);
assert(displayScoreHtml.includes('Opportunity 88/100'));
assert(displayScoreHtml.includes('>88<'));
assert(!displayScoreHtml.includes('market-score--risk'));

console.log('market row ui runtime contract: ok');
