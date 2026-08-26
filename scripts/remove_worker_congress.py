from pathlib import Path

p=Path('worker.js')
s=p.read_text()

start=s.find('async function fetchCongressTrades(')
end=s.find('\nexport default {', start)
if start<0 or end<0 or end<=start:
    raise SystemExit('Congress Worker function/export boundary not found')
block=s[start:end]
if 'www.bargo.ai/free-apis/congress' not in block:
    raise SystemExit('Congress function does not contain expected Bargo source')
if 'throw new Error(`Congress feed indisponível' not in block:
    raise SystemExit('Congress function end guard missing')
s=s[:start]+s[end+1:]

route='''      if (url.pathname === "/congress") {
        const ticker = url.searchParams.get("ticker") || "";
        const limit = url.searchParams.get("limit") || "100";
        const data = await fetchCongressTrades(ticker, limit);
        return new Response(JSON.stringify(data),
          { headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "public, max-age=300" } });
      }

'''
if route not in s:
    raise SystemExit('Worker /congress route not found')
s=s.replace(route,'',1)
old='endpoints: ["/quote?ticker=VWCE.DE", "/quotes?tickers=VWCE.DE,IWDA.L", "/market?ticker=MSFT", "/congress?ticker=NVDA", "/congress?limit=100"]'
new='endpoints: ["/quote?ticker=VWCE.DE", "/quotes?tickers=VWCE.DE,IWDA.L", "/market?ticker=MSFT"]'
if old not in s:
    raise SystemExit('Worker endpoint list not found')
s=s.replace(old,new,1)

if 'www.bargo.ai/free-apis/congress' in s or 'fetchCongressTrades' in s or 'url.pathname === "/congress"' in s:
    raise SystemExit('dead Congress Worker code remains')
if 'export default {' not in s or 'url.pathname === "/market"' not in s:
    raise SystemExit('Worker core routing damaged')
p.write_text(s)
print('removed dead Congress/Bargo Worker proxy')
