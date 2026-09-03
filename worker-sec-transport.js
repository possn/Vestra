const APP_ORIGIN = 'https://possn.github.io';
const SEC_BASE = 'https://data.sec.gov';
const SEC_USER_AGENT = 'Vestra/4.0 possn@users.noreply.github.com';
const MAX_CIK_DIGITS = 10;

function json(data, status=200, headers={}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      ...headers,
    },
  });
}

function cors(origin) {
  if (!origin) return {};
  const allowed = origin === APP_ORIGIN;
  return {
    'Access-Control-Allow-Origin': allowed ? origin : 'null',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Accept',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

export function normalizeCik(value) {
  const raw = String(value ?? '').trim();
  if (!/^\d{1,10}$/.test(raw)) return null;
  const n = Number(raw);
  if (!Number.isSafeInteger(n) || n <= 0) return null;
  return String(n).padStart(MAX_CIK_DIGITS, '0');
}

function endpointFor(pathname, cik) {
  if (pathname === '/sec/companyfacts') {
    return {
      family: 'companyfacts',
      url: `${SEC_BASE}/api/xbrl/companyfacts/CIK${cik}.json`,
      ttl: 21600,
    };
  }
  if (pathname === '/sec/submissions') {
    return {
      family: 'submissions',
      url: `${SEC_BASE}/submissions/CIK${cik}.json`,
      ttl: 3600,
    };
  }
  return null;
}

function validPayload(payload, family) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
  if (family === 'companyfacts') return !!payload.facts && typeof payload.facts === 'object' && !Array.isArray(payload.facts);
  if (family === 'submissions') return !!payload.filings && typeof payload.filings === 'object' && !Array.isArray(payload.filings);
  return false;
}

function cacheKey(endpoint, cik) {
  return new Request(`https://vestra.internal/sec-cache/${endpoint.family}/${cik}`);
}

export async function handleSecTransport(request, env={}, ctx=null, deps={}) {
  const url = new URL(request.url);
  const origin = request.headers.get('Origin') || '';
  const corsHeaders = cors(origin);
  if (request.method === 'OPTIONS') {
    if (origin && origin !== APP_ORIGIN) return new Response(null, {status: 403, headers: corsHeaders});
    return new Response(null, {status: 204, headers: corsHeaders});
  }
  if (request.method !== 'GET') return json({error: 'Método não suportado'}, 405, corsHeaders);
  if (origin && origin !== APP_ORIGIN) return json({error: 'Origem não autorizada'}, 403, corsHeaders);

  const cik = normalizeCik(url.searchParams.get('cik'));
  if (!cik) return json({error: 'CIK inválido'}, 400, corsHeaders);
  const endpoint = endpointFor(url.pathname, cik);
  if (!endpoint) return json({error: 'Endpoint SEC não suportado'}, 404, corsHeaders);

  const cache = deps.cache ?? (typeof caches !== 'undefined' ? caches.default : null);
  const key = cacheKey(endpoint, cik);
  if (cache) {
    const hit = await cache.match(key);
    if (hit) {
      const headers = new Headers(hit.headers);
      Object.entries(corsHeaders).forEach(([k,v]) => headers.set(k,v));
      headers.set('X-Vestra-Sec-Cache', 'hit');
      return new Response(hit.body, {status: hit.status, headers});
    }
  }

  const fetchImpl = deps.fetchImpl ?? fetch;
  let upstream;
  try {
    upstream = await fetchImpl(endpoint.url, {
      method: 'GET',
      headers: {
        'User-Agent': env.SEC_USER_AGENT || SEC_USER_AGENT,
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
      },
      cf: {cacheTtl: endpoint.ttl, cacheEverything: true},
    });
  } catch (_) {
    return json({error: 'SEC upstream indisponível'}, 502, corsHeaders);
  }

  if (!upstream.ok) {
    return json({error: 'SEC upstream indisponível', upstream_status: upstream.status}, 502, corsHeaders);
  }

  let payload;
  try {
    payload = await upstream.json();
  } catch (_) {
    return json({error: 'Resposta SEC inválida'}, 502, corsHeaders);
  }
  if (!validPayload(payload, endpoint.family)) return json({error: 'Payload SEC inválido'}, 502, corsHeaders);

  const response = json(payload, 200, {
    ...corsHeaders,
    'Cache-Control': `public, max-age=${endpoint.ttl}`,
    'X-Vestra-Sec-Source': 'sec.gov',
    'X-Vestra-Sec-Cache': 'miss',
  });
  if (cache) {
    const write = cache.put(key, response.clone());
    if (ctx?.waitUntil) ctx.waitUntil(write);
    else await write;
  }
  return response;
}

export const SEC_TRANSPORT_CAPABILITY = 'sec_transport';
