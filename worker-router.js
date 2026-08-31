import marketWorker from './worker.js';

const APP_ORIGIN = 'https://possn.github.io';
const MAX_LEARNED = 1500;
const ALLOWED_TYPES = new Set(['EQUITY','ETF','MUTUALFUND']);

function txt(v){ return String(v ?? '').trim(); }
function validTicker(v){ return /^[A-Z0-9][A-Z0-9.\-]{0,14}$/.test(txt(v).toUpperCase()); }
function isAllowedBrowserOrigin(origin){
  if (!origin) return false;
  if (origin === APP_ORIGIN) return true;
  try {
    const u = new URL(origin);
    return ['localhost','127.0.0.1','::1'].includes(u.hostname);
  } catch (_) { return false; }
}
function learnedCors(origin){
  const allowed = !origin || isAllowedBrowserOrigin(origin);
  return {
    'Access-Control-Allow-Origin': allowed ? (origin || '*') : 'null',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}
function json(data, status=200, headers={}){
  return new Response(JSON.stringify(data), {
    status,
    headers: {'Content-Type':'application/json','Cache-Control':'no-store',...headers},
  });
}

export class LearnedUniverse {
  constructor(ctx, env){ this.ctx = ctx; this.env = env; }

  async fetch(request){
    const url = new URL(request.url);
    if (request.method === 'GET') {
      const entries = await this.ctx.storage.list({prefix:'asset:'});
      const rows = [...entries.values()].sort((a,b)=>txt(b?.last_seen).localeCompare(txt(a?.last_seen)));
      return json({schema_version:1,count:rows.length,rows});
    }
    if (request.method === 'POST') {
      const input = await request.json().catch(()=>null);
      const ticker = txt(input?.ticker).toUpperCase();
      if (!validTicker(ticker)) return json({error:'ticker inválido'},400);
      const key = `asset:${ticker}`;
      const previous = await this.ctx.storage.get(key);
      if (!previous) {
        const count = Number(await this.ctx.storage.get('meta:count') || 0);
        if (count >= MAX_LEARNED) return json({error:'catálogo aprendido cheio'},507);
        await this.ctx.storage.put('meta:count', count + 1);
      }
      const now = new Date().toISOString();
      const row = {
        ticker,
        name: txt(input?.name || ticker),
        exchange: txt(input?.exchange),
        currency: txt(input?.currency).toUpperCase(),
        quote_type: txt(input?.quote_type || 'EQUITY').toUpperCase(),
        sector: txt(input?.sector),
        industry: txt(input?.industry),
        country: txt(input?.country),
        first_seen: previous?.first_seen || now,
        last_seen: now,
        validation_count: Number(previous?.validation_count || 0) + 1,
        source: 'vestra-global-search',
      };
      await this.ctx.storage.put(key,row);
      return json({ok:true,row});
    }
    return json({error:'Método não suportado'},405);
  }
}

async function learnedStub(env){
  if (!env?.LEARNED_UNIVERSE) return null;
  const id = env.LEARNED_UNIVERSE.idFromName('vestra-learned-universe-v1');
  return env.LEARNED_UNIVERSE.get(id);
}

async function validateLearnedTicker(ticker, env, ctx){
  const internal = new Request(`https://vestra.internal/quote?ticker=${encodeURIComponent(ticker)}`);
  const response = await marketWorker.fetch(internal, env, ctx);
  if (!response.ok) return null;
  const quote = await response.json().catch(()=>null);
  const type = txt(quote?.quote_type).toUpperCase();
  const price = Number(quote?.price);
  if (!quote || quote.error || !Number.isFinite(price) || price <= 0) return null;
  if (type && !ALLOWED_TYPES.has(type)) return null;
  const canonical = txt(quote.ticker || ticker).toUpperCase();
  if (!validTicker(canonical)) return null;
  return {
    ticker: canonical,
    name: txt(quote.name || canonical),
    exchange: txt(quote.exchange),
    currency: txt(quote.currency).toUpperCase(),
    quote_type: type || 'EQUITY',
    sector: txt(quote.sector),
    industry: txt(quote.industry),
    country: txt(quote.country),
  };
}

async function handleLearnedUniverse(request, env, ctx){
  const origin = request.headers.get('Origin') || '';
  const cors = learnedCors(origin);
  if (request.method === 'OPTIONS') return new Response(null,{status:204,headers:cors});
  const stub = await learnedStub(env);
  if (!stub) return json({error:'Learned universe storage unavailable'},503,cors);

  if (request.method === 'GET') {
    const response = await stub.fetch('https://learned.internal/list');
    const payload = await response.json().catch(()=>({schema_version:1,count:0,rows:[]}));
    return json(payload,response.status,cors);
  }

  if (request.method === 'POST') {
    if (!isAllowedBrowserOrigin(origin)) return json({error:'Origem não autorizada'},403,cors);
    const input = await request.json().catch(()=>null);
    const ticker = txt(input?.ticker).toUpperCase();
    if (!validTicker(ticker)) return json({error:'ticker inválido'},400,cors);
    const validated = await validateLearnedTicker(ticker,env,ctx);
    if (!validated) return json({error:'Ativo não validado'},422,cors);
    const response = await stub.fetch('https://learned.internal/asset',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(validated)
    });
    const payload = await response.json().catch(()=>({error:'Falha de persistência'}));
    return json(payload,response.status,cors);
  }

  return json({error:'Método não suportado'},405,cors);
}

export default {
  async fetch(request, env, ctx){
    const url = new URL(request.url);
    if (url.pathname === '/learned-universe') return handleLearnedUniverse(request,env,ctx);

    if (url.pathname === '/health' && request.method === 'GET') {
      const response = await marketWorker.fetch(request,env,ctx);
      const payload = await response.json().catch(()=>({}));
      const capabilities = Array.from(new Set([...(payload.capabilities || []),'learned_universe']));
      return json({...payload,capabilities,learned_universe_storage:'durable_object'},response.status,Object.fromEntries(response.headers));
    }

    return marketWorker.fetch(request,env,ctx);
  }
};
