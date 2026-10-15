const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const text=fs.readFileSync('market-opportunities.js','utf8');
const a=text.indexOf('  let prebreakoutObservations=[];'),b=text.indexOf('  function stocks(){',a);
assert(a>=0&&b>a);
const context={Date,Number,Map,Set,console,fetch:async()=>({ok:false}),activeLens:'breakout',prebreakoutFeed:new Map(),opportunities:()=>{},t:v=>String(v??'').trim(),esc:v=>String(v)};
vm.createContext(context);
vm.runInContext(text.slice(a,b)+';this.read=()=>({status:prebreakoutHistoryStatus,render:renderPrebreakoutHistory});',context);
let container={innerHTML:''};
const section={querySelector:selector=>selector==='.vestra-prebreakout-history'?container:{insertAdjacentElement:()=>{}}};
(async()=>{
 await context.loadPrebreakoutObservations();
 assert.equal(context.read().status,'unavailable');
 context.read().render(section);
 assert.match(container.innerHTML,/Histórico ainda não publicado/);
 assert.doesNotMatch(container.innerHTML,/Sem observações anteriores verificadas/);
 console.log('Missing historical index displays an explicit availability state');
})().catch(e=>{console.error(e);process.exitCode=1});
