const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');

(async()=>{
  let releaseExecutive;
  const pendingExecutive=new Promise(resolve=>{releaseExecutive=resolve;});
  const today=new Date().toISOString().slice(0,10);
  const house={schema_version:2,newest_disclosure:today,source_last_updated:today,
    members:[{key:'congress:fixture-house',name:'Fixture House',chamber:'House'}],
    trades:[{ticker:'AAA',member:'Fixture House',member_key:'congress:fixture-house',
             chamber:'House',type:'purchase',transaction_date:today,disclosure_date:today}]};
  const executive={people:[{key:'executive:fixture-person',name:'Fixture Executive',chamber:'Executive'}],trades:[]};
  const fetch=async url=>{
    if(url.includes('politicians.json'))return {ok:true,json:async()=>house};
    if(url.includes('executives.json')){
      await pendingExecutive;
      return {ok:true,json:async()=>executive};
    }
    throw Error('Unexpected URL '+url);
  };
  const file=fs.readFileSync(path.join(__dirname,'..','politicians.js'),'utf8');
  assert.match(file,/\}\)\(\);\s*$/);
  const source=file.replace(/\}\)\(\);\s*$/,`
    globalThis.__politicianSnapshotTest={
      load:()=>loadBase(),
      counts:()=>({members:memberDirectory.length,trades:recentTrades.length}),
      names:()=>memberDirectory.map(x=>x.name)
    };
  })();`);
  const sandbox={fetch,document:{readyState:'loading',addEventListener(){}},console,Date};
  vm.createContext(sandbox);
  vm.runInContext(source,sandbox,{filename:'politicians.js'});
  const app=sandbox.__politicianSnapshotTest;
  const pending=app.load();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(app.counts().members,0,'no half-hydrated members while executive fetch is pending');
  assert.equal(app.counts().trades,0,'no half-hydrated trades while executive fetch is pending');
  releaseExecutive();
  await pending;
  assert.equal(app.counts().members,2);
  assert.equal(app.counts().trades,1);
  assert.deepEqual(Array.from(app.names()),['Fixture Executive','Fixture House'].sort((a,b)=>a.startsWith('Fixture Executive')?-1:1));
  console.log('politician atomic feed regression: ok');
})().catch(e=>{console.error(e);process.exitCode=1;});
