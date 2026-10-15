const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('market-opportunities.js','utf8');
const from=source.indexOf('  async function loadPrebreakoutFeed(){');
const to=source.indexOf('  function stocks(){',from);
assert(from>=0&&to>from);
async function check(hours,expected){
 let called=0;
 const context={
  fetch:async()=>({ok:true,json:async()=>({schema:'vestra_prebreakout_v1',generated_at:new Date(Date.now()-hours*3600000).toISOString(),signals:[{ticker:'AAA',date:new Date().toISOString().slice(0,10),stage:'compressão',score:66,widthPct:10,source:'yahoo:daily_ohlcv'}]})}),
  Date,Map,Number,console,Math,
  activeLens:'breakout',
  opportunities:()=>{called++},
  prebreakoutFeed:new Map(),
  prebreakoutFeedAuthoritative:false,
  t:v=>String(v??'').trim()
 };
 vm.createContext(context);
 vm.runInContext(source.slice(from,to)+';this.read=()=>({feed:prebreakoutFeed,authoritative:prebreakoutFeedAuthoritative});',context);
 await context.loadPrebreakoutFeed();
 const result=context.read();
 assert.equal(result.feed.has('AAA'),expected);
 assert.equal(result.authoritative,true);
 assert.equal(called,1);
}
(async()=>{await check(2,true);await check(37,false);console.log('Prebreakout freshness contract passed')})().catch(e=>{console.error(e);process.exitCode=1});
