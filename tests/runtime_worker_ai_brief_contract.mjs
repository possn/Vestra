import assert from 'node:assert/strict';
import {
  AI_BRIEF_MODEL,
  AI_BRIEF_SCHEMA,
  normalizeEvidence,
  normalizeBrief,
  handleAiBrief,
} from '../worker-ai-brief.js';

class MemoryCache {
  constructor(){ this.rows=new Map(); }
  async match(key){ const r=this.rows.get(String(key)); return r ? r.clone() : undefined; }
  async put(key,response){ this.rows.set(String(key),response.clone()); }
}

function request(body, extra={}){
  return new Request('https://vestra.test/ai-brief',{
    method:'POST',
    headers:{
      'Content-Type':'application/json',
      'Origin':'https://possn.github.io',
      'X-Vestra-Session':'session-contract-1234',
      ...(extra.headers||{}),
    },
    body:JSON.stringify(body),
  });
}

const normalized=normalizeEvidence({ticker:' msft ',score:null,confidence:'',roe:'0.25',business_summary:'x'.repeat(6000)});
assert.equal(normalized.ticker,'MSFT');
assert.equal(normalized.score,null,'missing score must remain null');
assert.equal(normalized.confidence,null,'blank confidence must remain null');
assert.equal(normalized.roe,0.25);
assert.equal(normalized.business_summary.length,5000,'summary must be bounded');
assert.equal(AI_BRIEF_SCHEMA.additionalProperties,false);

assert.equal(normalizeBrief({response:{thesis:'Comprar já',why_now:'agora',risks:[],catalysts:[],what_changes_the_thesis:'nada'}}),null,
  'direct trading instructions must fail closed');

const optionsReq=new Request('https://vestra.test/ai-brief',{
  method:'OPTIONS',headers:{Origin:'https://possn.github.io','Access-Control-Request-Headers':'content-type,x-vestra-session'}
});
const optionsResp=await handleAiBrief(optionsReq,{},null,{cache:null});
assert.equal(optionsResp.status,204);
assert.match(optionsResp.headers.get('Access-Control-Allow-Headers')||'',/X-Vestra-Session/i);

const forbidden=await handleAiBrief(request({type:'company_brief',version:'1',data:{ticker:'MSFT'}},{headers:{Origin:'https://example.invalid'}}),{},null,{cache:null});
assert.equal(forbidden.status,403);

const unavailable=await handleAiBrief(request({type:'company_brief',version:'1',data:{ticker:'MSFT'}}),{},null,{cache:null});
assert.equal(unavailable.status,503,'missing AI binding must degrade safely');

let aiCalls=0;
let captured=null;
let limiterCalls=0;
const env={
  AI:{
    async run(model,payload){
      aiCalls+=1; captured={model,payload};
      return {response:{
        thesis:'Qualidade operacional sustentada pela evidência fornecida.',
        why_now:'Estimativas e recuperação justificam acompanhamento.',
        risks:['Cobertura ainda incompleta.'],
        catalysts:['Melhoria de estimativas.'],
        what_changes_the_thesis:'Deterioração material de crescimento ou cash flow.',
      }};
    },
  },
  AI_BRIEF_RATE_LIMITER:{ async limit({key}){ limiterCalls+=1; assert.match(key,/session-contract-1234/); return {success:true}; } },
};
const cache=new MemoryCache();
const pending=[];
const ctx={waitUntil(p){pending.push(Promise.resolve(p));}};
const body={type:'company_brief',version:'1',data:{ticker:'MSFT',score:73,confidence:82,coverage:78,roe:0.22,business_summary:'Software company.'}};
const first=await handleAiBrief(request(body),env,ctx,{cache,timeoutMs:1000});
assert.equal(first.status,200);
const firstJson=await first.json();
assert.equal(firstJson.brief.thesis,'Qualidade operacional sustentada pela evidência fornecida.');
assert.equal(firstJson.model,AI_BRIEF_MODEL);
assert.equal(firstJson.cached,false);
assert.equal(aiCalls,1);
assert.equal(captured.model,AI_BRIEF_MODEL);
assert.equal(captured.payload.response_format.type,'json_schema');
assert.deepEqual(captured.payload.response_format.json_schema,AI_BRIEF_SCHEMA);
assert.equal(captured.payload.temperature,0.2);
const prompt=JSON.stringify(captured.payload.messages);
assert.match(prompt,/EXCLUSIVAMENTE/);
assert.match(prompt,/Não dês instruções de comprar, vender/);
assert.match(prompt,/Campos null ou vazios/);
await Promise.all(pending);

const second=await handleAiBrief(request(body),env,ctx,{cache,timeoutMs:1000});
const secondJson=await second.json();
assert.equal(second.status,200);
assert.equal(secondJson.cached,true,'same evidence must reuse cached brief');
assert.equal(aiCalls,1,'cache must avoid a second model call');
assert.equal(limiterCalls,2,'every public request remains rate limited');

const limitedEnv={AI:env.AI,AI_BRIEF_RATE_LIMITER:{async limit(){return {success:false};}}};
const limited=await handleAiBrief(request(body),limitedEnv,null,{cache:null});
assert.equal(limited.status,429);
assert.equal(limited.headers.get('Retry-After'),'60');

console.log('worker AI brief contract: ok');
