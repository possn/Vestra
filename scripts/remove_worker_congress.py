from pathlib import Path
import re

p=Path('worker.js')
s=p.read_text()

start=s.find('async function fetchCongressTrades(')
if start<0:
    raise SystemExit('fetchCongressTrades not found')
# remove exact top-level function through next top-level function declaration
m=re.search(r'(?m)^async function |^function ', s[start+1:])
if not m:
    raise SystemExit('next Worker function not found')
end=start+1+m.start()
block=s[start:end]
if 'www.bargo.ai/free-apis/congress' not in block:
    raise SystemExit('Congress function does not contain expected Bargo source')
s=s[:start]+s[end:]

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
p.write_text(s)
print('removed dead Congress/Bargo Worker proxy')
