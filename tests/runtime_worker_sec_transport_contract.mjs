import assert from 'node:assert/strict';
import {handleSecTransport, normalizeCik, SEC_TRANSPORT_CAPABILITY} from '../worker-sec-transport.js';

class MemoryCache {
  constructor(){ this.rows = new Map(); }
  async match(key){ const v=this.rows.get(String(key)); return v ? v.clone() : undefined; }
  async put(key,response){ this.rows.set(String(key),response.clone()); }
}

assert.equal(SEC_TRANSPORT_CAPABILITY,'sec_transport');
assert.equal(normalizeCik('320193'),'0000320193');
assert.equal(normalizeCik('0000320193'),'0000320193');
assert.equal(normalizeCik(''),null);
assert.equal(normalizeCik('abc'),null);
assert.equal(normalizeCik('12345678901'),null);

let calls=[];
const fetchImpl=async (url, options)=>{
  calls.push({url, options});
  if (url.includes('/companyfacts/')) {
    return new Response(JSON.stringify({cik:320193,facts:{'us-gaap':{Assets:{}}}}),{status:200,headers:{'Content-Type':'application/json'}});
  }
  return new Response(JSON.stringify({cik:'0000320193',filings:{recent:{form:['10-K']}}}),{status:200,headers:{'Content-Type':'application/json'}});
};
const cache=new MemoryCache();
const pending=[];
const ctx={waitUntil(p){ pending.push(Promise.resolve(p)); }};

let response=await handleSecTransport(
  new Request('https://vestra.test/sec/companyfacts?cik=320193'),
  {},ctx,{fetchImpl,cache}
);
assert.equal(response.status,200);
assert.equal(response.headers.get('X-Vestra-Sec-Source'),'sec.gov');
assert.equal(response.headers.get('X-Vestra-Sec-Cache'),'miss');
let payload=await response.json();
assert.ok(payload.facts);
assert.equal(calls.length,1);
assert.equal(calls[0].url,'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json');
assert.match(calls[0].options.headers['User-Agent'],/Vestra\/4\.0/);
assert.match(calls[0].options.headers['User-Agent'],/@/);
await Promise.all(pending);

response=await handleSecTransport(
  new Request('https://vestra.test/sec/companyfacts?cik=320193'),
  {},null,{fetchImpl,cache}
);
assert.equal(response.status,200);
assert.equal(response.headers.get('X-Vestra-Sec-Cache'),'hit');
assert.equal(calls.length,1,'cache hit must avoid SEC request');

response=await handleSecTransport(
  new Request('https://vestra.test/sec/submissions?cik=320193'),
  {},null,{fetchImpl,cache:null}
);
assert.equal(response.status,200);
payload=await response.json();
assert.ok(payload.filings);
assert.equal(calls.at(-1).url,'https://data.sec.gov/submissions/CIK0000320193.json');

response=await handleSecTransport(new Request('https://vestra.test/sec/companyfacts?cik=ABC'),{},null,{fetchImpl,cache:null});
assert.equal(response.status,400);
response=await handleSecTransport(new Request('https://vestra.test/sec/companyfacts?cik=320193',{method:'POST'}),{},null,{fetchImpl,cache:null});
assert.equal(response.status,405);
response=await handleSecTransport(new Request('https://vestra.test/sec/companyfacts?cik=320193',{headers:{Origin:'https://example.invalid'}}),{},null,{fetchImpl,cache:null});
assert.equal(response.status,403);

const badFetch=async ()=>new Response('<html>blocked</html>',{status:403,headers:{'Content-Type':'text/html'}});
response=await handleSecTransport(new Request('https://vestra.test/sec/companyfacts?cik=320193'),{},null,{fetchImpl:badFetch,cache:null});
assert.equal(response.status,502);
payload=await response.json();
assert.equal(payload.upstream_status,403);

const invalidPayloadFetch=async ()=>new Response(JSON.stringify({hello:'world'}),{status:200,headers:{'Content-Type':'application/json'}});
response=await handleSecTransport(new Request('https://vestra.test/sec/companyfacts?cik=320193'),{},null,{fetchImpl:invalidPayloadFetch,cache:null});
assert.equal(response.status,502);

console.log('worker SEC transport contract: ok');
