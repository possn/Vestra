const fs=require('fs');
const vm=require('vm');
const assert=require('assert');

const context={window:{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('market-search-suggestions.js','utf8'),context,{filename:'market-search-suggestions.js'});
assert.equal(context.window.VestraMarketSearchSuggestions?.version,'1.0');

const stocks=[
  {ticker:'MSFT',name:'Microsoft Corporation',sector:'Technology',score:91},
  {ticker:'META',name:'Meta Platforms',sector:'Technology',score:85},
  {ticker:'MSTR',name:'Strategy',sector:'Technology',score:60},
  {ticker:'VWCE.DE',name:'Vanguard FTSE All-World UCITS ETF',quote_type:'ETF',score:80},
  {ticker:'ABC',name:'Microsoft Supplier',sector:'Industrials',score:70},
];
const box={hidden:true,innerHTML:''};
let query='';
const txt=v=>String(v??'').trim();
const n=v=>{ if(v===null||v===undefined||v==='') return null; const x=Number(v); return Number.isFinite(x)?x:null; };
const esc=v=>txt(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api=context.window.VestraMarketSearchSuggestions.create({
  getStocks:()=>stocks,
  getQuery:()=>query,
  isLoaded:()=>true,
  getBox:()=>box,
  text:txt,
  number:n,
  escapeHtml:esc,
  isFund:x=>x.quote_type==='ETF',
});

assert.deepEqual(Array.from(api.matches('',7)),[]);
assert.equal(api.matches('msft',7)[0].ticker,'MSFT');
assert.equal(api.matches('ms',7)[0].ticker,'MSFT');
assert.equal(api.matches('microsoft',7)[0].ticker,'MSFT');
assert.equal(api.matches('meta',7)[0].ticker,'META');
assert.equal(api.matches('world',7)[0].ticker,'VWCE.DE');
assert.equal(api.matches('m',2).length,2);

query='vwce';
api.render();
assert.equal(box.hidden,false);
assert(box.innerHTML.includes('VWCE.DE'));
assert(box.innerHTML.includes('ETF/Fundo'));

query='does-not-exist';
api.render();
assert(box.innerHTML.includes('Sem correspondências imediatas'));
assert.equal(box.hidden,false);

query='';
api.render();
assert.equal(box.hidden,true);
assert.equal(box.innerHTML,'');

console.log('market search suggestions runtime contract: ok');
