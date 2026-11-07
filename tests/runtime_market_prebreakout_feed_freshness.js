const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('market-opportunities.js','utf8');
const from=source.indexOf('  async function loadPrebreakoutFeed(){');
const to=source.indexOf('  function stocks(){',from);
assert(from>=0&&to>from);
async function check(hours,expected,coverage=50,quality=coverage){
 let called=0;
 const context={
  fetch:async()=>({ok:true,json:async()=>({schema:'vestra_prebreakout_v1',generated_at:new Date(Date.now()-hours*3600000).toISOString(),coverage_audit_24h:{coverage_pct:coverage},scan_quality_audit:{observed_24h_coverage_pct:quality},signals:[{ticker:'AAA',date:new Date().toISOString().slice(0,10),stage:'compressão',score:66,widthPct:10,source:'yahoo:daily_ohlcv'}]})}),
  Date,Map,Number,console,Math,
  activeLens:'breakout',
  opportunities:()=>{called++},
  prebreakoutFeed:new Map(),
  prebreakoutFeedAuthoritative:false,
  t:v=>String(v??'').trim()
 };
 vm.createContext(context);
 vm.runInContext(source.slice(from,to)+';this.read=()=>({feed:prebreakoutFeed,authoritative:prebreakoutFeedAuthoritative,status:prebreakoutFeedStatus});',context);
 await context.loadPrebreakoutFeed();
 const result=context.read();
 assert.equal(result.feed.has('AAA'),expected);
 assert.equal(result.authoritative,true);
 if(coverage>100||coverage<0||quality>100||quality<0||Math.abs(coverage-quality)>0.01)assert.equal(result.status,'unavailable');
 assert.equal(called,1);
}
(async()=>{await check(2,true);await check(37,false);await check(2,false,105.18,105.18);await check(2,false,50,105.18);await check(2,false,50,51);console.log('Prebreakout freshness and coverage contract passed')})().catch(e=>{console.error(e);process.exitCode=1});
