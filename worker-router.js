import marketWorker from './worker.js';
import { handleAiBrief, AI_BRIEF_MODEL } from './worker-ai-brief.js';
import { handleSecTransport, SEC_TRANSPORT_CAPABILITY } from './worker-sec-transport.js';

const APP_ORIGIN = 'https://possn.github.io';
const MAX_LEARNED = 1500;
const LEARNED_NAMESPACE = 'vestra-learned-universe-v2';
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
      return json({schema_version:2,count:rows.length,rows});
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
  const id = env.LEARNED_UNIVERSE.idFromName(LEARNED_NAMESPACE);
  return env.LEARNED_UNIVERSE.get(id);
}

async function fetchYahooExactIdentity(ticker){
  const headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept':'application/json,text/plain,*/*',
    'Accept-Language':'en-US,en;q=0.9',
  };
  const quoteUrls = [
    `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(ticker)}`,
    `https://query2.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(ticker)}`,
  ];
  for (const target of quoteUrls) {
    try {
      const response = await fetch(target,{headers});
      if (!response.ok) continue;
      const payload = await response.json().catch(()=>null);
      const row = (payload?.quoteResponse?.result || []).find(item=>txt(item?.symbol).toUpperCase()===ticker);
      const type = txt(row?.quoteType).toUpperCase();
      if (row && (!type || ALLOWED_TYPES.has(type))) {
        return {symbol:ticker,quote_type:type,exchange:txt(row.exchange || row.fullExchangeName)};
      }
    } catch (_) {}
  }

  const chartUrls = [
    `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`,
    `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`,
  ];
  for (const target of chartUrls) {
    try {
      const response = await fetch(target,{headers});
      if (!response.ok) continue;
      const payload = await response.json().catch(()=>null);
      const meta = payload?.chart?.result?.[0]?.meta;
      const symbol = txt(meta?.symbol).toUpperCase();
      const type = txt(meta?.instrumentType).toUpperCase();
      if (meta && symbol === ticker && (!type || ALLOWED_TYPES.has(type))) {
        return {symbol,quote_type:type,exchange:txt(meta.exchangeName)};
      }
    } catch (_) {}
  }
  return null;
}

async function validateLearnedTicker(ticker, env, ctx){
  const exactIdentity = await fetchYahooExactIdentity(ticker);
  if (!exactIdentity || exactIdentity.symbol !== ticker) return null;

  const internal = new Request(`https://vestra.internal/quote?ticker=${encodeURIComponent(ticker)}`);
  const response = await marketWorker.fetch(internal, env, ctx);
  if (!response.ok) return null;
  const quote = await response.json().catch(()=>null);
  const type = txt(quote?.quote_type || exactIdentity.quote_type).toUpperCase();
  const price = Number(quote?.price);
  if (!quote || quote.error || !Number.isFinite(price) || price <= 0) return null;
  if (type && !ALLOWED_TYPES.has(type)) return null;
  const canonical = txt(quote.ticker || ticker).toUpperCase();
  const retrieval = txt(quote.retrieval_ticker || canonical).toUpperCase();
  if (!validTicker(canonical) || canonical !== ticker || retrieval !== ticker) return null;
  return {
    ticker,
    name: txt(quote.name || ticker),
    exchange: txt(quote.exchange || exactIdentity.exchange),
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
    const payload = await response.json().catch(()=>({schema_version:2,count:0,rows:[]}));
    return json(payload,response.status,cors);
  }

  if (request.method === 'POST') {
    if (!isAllowedBrowserOrigin(origin)) return json({error:'Origem não autorizada'},403,cors);
    const input = await request.json().catch(()=>null);
    const ticker = txt(input?.ticker).toUpperCase();
    if (!validTicker(ticker)) return json({error:'ticker inválido'},400,cors);
    const validated = await validateLearnedTicker(ticker,env,ctx);
    if (!validated) return json({error:'Ativo não validado por identidade exata'},422,cors);
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
    if (url.pathname === '/ai-brief') return handleAiBrief(request,env,ctx);
    if (url.pathname === '/sec/companyfacts' || url.pathname === '/sec/submissions') return handleSecTransport(request,env,ctx);

    if (url.pathname === '/health' && request.method === 'GET') {
      const response = await marketWorker.fetch(request,env,ctx);
      const payload = await response.json().catch(()=>({}));
      const capabilities = Array.from(new Set([...(payload.capabilities || []),'learned_universe','ai_brief']));
      const experimentalCapabilities = Array.from(new Set([...(payload.experimental_capabilities || []),SEC_TRANSPORT_CAPABILITY]));
      return json({
        ...payload,
        capabilities,
        experimental_capabilities:experimentalCapabilities,
        learned_universe_storage:'durable_object_v2_exact_identity',
        ai_brief_provider:'workers_ai',
        ai_brief_model:AI_BRIEF_MODEL,
        ai_brief_rate_limit: env?.AI_BRIEF_RATE_LIMITER ? 'binding' : 'unavailable',
        sec_transport:{
          status:'experimental_not_in_pipeline',
          upstream:'sec.gov',
          routes:['companyfacts','submissions'],
        },
      },response.status,Object.fromEntries(response.headers));
    }

    return marketWorker.fetch(request,env,ctx);
  }
};
