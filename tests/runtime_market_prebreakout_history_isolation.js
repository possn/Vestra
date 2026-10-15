const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('market-opportunities.js','utf8');
const a=source.indexOf('  let prebreakoutObservations=[];');
const b=source.indexOf('  function stocks(){',a);
assert(a>0&&b>a,'history loader/renderer must exist');
const body=source.slice(a,b);
assert.match(source,/loadPrebreakoutObservations\(\);/);
assert.match(source,/renderPrebreakoutHistory\(section\);/);
const container={
  innerHTML:'',
  querySelector:()=>null,
  insertAdjacentElement:()=>{}
};
const section={
  querySelector:s=>s==='.vestra-prebreakout-history'?container:{insertAdjacentElement:()=>{}}
};
const context={
  fetch:async()=>({ok:true,json:async()=>({
   schema:'vestra_prebreakout_observations_v1',historical_only:true,
   generated_at:new Date().toISOString(),
   observations:[{ticker:'AAA',stage:'compressão',observed_at:new Date().toISOString(),current:false},
                 {ticker:'LIVE',stage:'confirmado',observed_at:new Date().toISOString(),current:false},
                 {ticker:'BAD',stage:'pré-breakout',observed_at:new Date().toISOString(),current:true}]
  })}),
  Date,Number,console,Math,Set,Array,JSON,
  activeLens:'breakout',prebreakoutFeed:new Map([['LIVE',{}]]),
  opportunities:()=>{},t:v=>String(v??'').trim(),
  esc:v=>String(v)
};
vm.createContext(context);
vm.runInContext(body+';this.check=()=>({items:prebreakoutObservations,render:renderPrebreakoutHistory});',context);
(async()=>{
 await context.loadPrebreakoutObservations();
 const {items,render}=context.check();
 assert.equal(items.length,2);
 render(section);
 assert.match(container.innerHTML,/AAA/);
 assert.doesNotMatch(container.innerHTML,/LIVE|BAD/);
 assert.match(container.innerHTML,/não são sinais atuais/);
 console.log('Historical observations remain isolated from current breakout signals');
})().catch(err=>{console.error(err);process.exitCode=1});
