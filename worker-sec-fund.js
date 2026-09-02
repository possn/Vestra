const SEC_FUND_URL = 'https://www.sec.gov/files/company_tickers_mf.json';
const CACHE_SECONDS = 6 * 60 * 60;

function validPayload(payload){
  if(!payload || !Array.isArray(payload.fields) || !Array.isArray(payload.data) || payload.data.length < 1000) return false;
  const fields = payload.fields.map(x => String(x || '').trim().toLowerCase());
  return fields.includes('cik') && fields.includes('symbol');
}

export async function handleSecFundMap(request){
  if(request.method !== 'GET') return new Response(JSON.stringify({error:'Método não suportado'}),{
    status:405,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}
  });

  const cache = caches.default;
  const cacheKey = new Request('https://vestra.internal/sec-fund-map-v1');
  const cached = await cache.match(cacheKey);
  if(cached) return cached;

  const upstream = await fetch(SEC_FUND_URL,{
    headers:{
      'User-Agent':'Vestra/4.0 (+https://github.com/possn/Vestra)',
      'Accept':'application/json',
      'Accept-Encoding':'gzip, deflate',
    },
  });
  if(!upstream.ok){
    return new Response(JSON.stringify({error:'SEC fund map unavailable',upstream_status:upstream.status}),{
      status:502,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}
    });
  }

  const payload = await upstream.json().catch(()=>null);
  if(!validPayload(payload)){
    return new Response(JSON.stringify({error:'SEC fund map invalid'}),{
      status:502,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}
    });
  }

  const response = new Response(JSON.stringify(payload),{
    status:200,
    headers:{
      'Content-Type':'application/json',
      'Cache-Control':`public, max-age=${CACHE_SECONDS}`,
      'X-Vestra-Source':SEC_FUND_URL,
      'X-Vestra-Transport':'cloudflare-worker',
    },
  });
  await cache.put(cacheKey,response.clone());
  return response;
}

export { SEC_FUND_URL };
