const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('market-opportunities.js', 'utf8');
const begin = source.indexOf('  let prebreakoutFeed=new Map();');
const end = source.indexOf('  function stocks(){', begin);
assert(begin >= 0 && end > begin);
const now = new Date();
const make = (attempted, evaluable, hours=1) => ({
  schema: 'vestra_prebreakout_v1',
  generated_at: new Date(now.getTime()-hours*3600000).toISOString(),
  signals: [],
  scan_slot_telemetry: {rows_attempted:attempted, rows_evaluable:evaluable},
  scan_quality_audit:{observed_24h_coverage_pct:50},
  coverage_audit_24h:{coverage_pct:50}
});

async function verify(payload) {
  let refreshed=0;
  const sandbox = {
    Date, Number, Map, Math, console,
    activeLens:'breakout',
    opportunities:()=>{refreshed++},
    fetch:async()=>({ok:true,json:async()=>payload}),
    t:v=>String(v??'').trim(),
    n:v=>{
      if(v===null||v===undefined||v==='')return null;
      const n=Number(v);
      return Number.isFinite(n)?n:null;
    }
  };
  vm.createContext(sandbox);
  vm.runInContext(source.slice(begin,end)+
    ';this.state=()=>({status:prebreakoutFeedStatus,authoritative:prebreakoutFeedAuthoritative,copy:prebreakoutEmptyCopy(),date:prebreakoutProvenanceLabel(),quality:prebreakoutSlotEvidence,items:prebreakoutFeed.size});',sandbox);
  await sandbox.loadPrebreakoutFeed();
  assert.equal(refreshed,1);
  return sandbox.state();
}
(async()=>{
  const none=await verify(make(300,0));
  assert.equal(none.status,'ready');
  assert.equal(none.authoritative,true);
  assert.equal(none.items,0);
  assert.match(none.copy,/inconclusivo.*300 ativos.*nenhum|inconclusivo.*300 ativos/i);
  assert.match(none.copy,/histórico OHLCV avaliável/);
  assert.match(none.date,/Pré-breakout.*\d{2}\/\d{2}/);

  const genuine=await verify(make(300,50));
  assert.equal(genuine.status,'ready');
  assert.match(genuine.copy,/Sem sinais de pré-breakout elegíveis/);
  assert.doesNotMatch(genuine.copy,/inconclusivo/);

  const noQuality=await verify({...make(300,50),scan_slot_telemetry:undefined});
  assert.match(noQuality.copy,/Sem sinais de pré-breakout elegíveis/);

  const corrupt=await verify(make(10,11));
  assert.match(corrupt.copy,/Sem sinais de pré-breakout elegíveis/);

  const stale=await verify(make(300,0,40));
  assert.equal(stale.status,'outdated');
  assert.match(stale.copy,/desatualizado/);
  assert.match(stale.date,/desatualizado/);
  console.log('Prebreakout: distinguish zero-evaluable from zero-signals and dated provenance.');
})().catch(error=>{console.error(error);process.exitCode=1;});
