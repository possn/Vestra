from pathlib import Path

p=Path('market.js')
s=p.read_text()
start=s.find('  function normalizeCongressLive(x){')
end=s.find("  const WATCH_KEY = 'vestra-market-watchlist-v1';", start)
if start<0 or end<0 or end<=start:
    raise SystemExit('Congress live block markers not found')
old=s[start:end]
for probe in ['www.bargo.ai/free-apis/congress/v1/trades','/congress?','async function loadCongressLive']:
    if probe not in old:
        raise SystemExit(f'expected legacy Congress probe missing: {probe}')
new="""  function normalizeCongressLive(x){
    return {
      ticker: txt(x?.ticker).toUpperCase(),
      representative: txt(x?.representative||x?.member||x?.name)||'Membro do Congresso',
      chamber: txt(x?.chamber), state: txt(x?.state), party: txt(x?.party),
      type: txt(x?.type||x?.transaction)||'trade',
      amount: txt(x?.amount||x?.amount_range)||'—',
      transaction_date: txt(x?.transaction_date||x?.date),
      disclosure_date: txt(x?.disclosure_date||x?.filed_date),
      asset: txt(x?.asset), filing_url: txt(x?.filing_url||x?.filing_portal)
    };
  }

  function politiciansSnapshotFresh(d){
    if(!d || Number(d.schema_version||0)<2 || !Array.isArray(d.trades)) return false;
    const newest=txt(d.newest_disclosure||d.source_last_updated).slice(0,10);
    const ms=newest?new Date(`${newest}T00:00:00Z`).valueOf():NaN;
    if(!Number.isFinite(ms)) return false;
    return (Date.now()-ms) <= 60*86400000;
  }

  function attachCongressToStocks(trades){
    const grouped=new Map();
    for(const tr of trades){
      const tk=txt(tr.ticker).toUpperCase().split('.')[0];
      if(!tk) continue;
      if(!grouped.has(tk)) grouped.set(tk,[]);
      grouped.get(tk).push(tr);
    }
    for(const [tk,rows] of grouped){
      const stock=M.byTicker.get(tk) || [...M.byTicker.values()].find(x=>txt(x.ticker).toUpperCase().split('.')[0]===tk);
      if(!stock) continue;
      const cur=Array.isArray(stock.congress_trades)?stock.congress_trades:[];
      const key=x=>`${txt(x.transaction_date||x.date)}|${txt(x.representative||x.member||x.name)}|${txt(x.type)}|${txt(x.amount||x.amount_range)}|${txt(x.asset)}`;
      const seen=new Set(cur.map(key));
      const additions=rows.filter(x=>!seen.has(key(x)));
      stock.congress_trades=[...cur,...additions];
    }
  }

  async function loadCongressLive(ticker=''){
    const tk=txt(ticker).toUpperCase().split('.')[0];
    if(M.congressLoaded){
      return tk ? M.congressLive.filter(x=>x.ticker.split('.')[0]===tk) : M.congressLive;
    }
    if(M.congressLoading){
      const all=await M.congressLoading;
      return tk ? all.filter(x=>x.ticker.split('.')[0]===tk) : all;
    }

    M.congressLoading=(async()=>{
      const cacheKey='vestra-congress-canonical-v3';
      const cacheMaxAge=6*60*60*1000;
      try{
        try{
          const cached=JSON.parse(localStorage.getItem(cacheKey)||'null');
          if(cached && Array.isArray(cached.trades) && Date.now()-Number(cached.ts||0)<cacheMaxAge){
            M.congressLive=cached.trades.map(normalizeCongressLive).filter(x=>x.ticker);
            M.congressLoaded=true; M.congressError='';
            attachCongressToStocks(M.congressLive);
            return M.congressLive;
          }
        }catch(_){}

        const r=await fetch(`./data/politicians.json?ts=${Date.now()}`,{cache:'no-store'});
        if(!r.ok) throw new Error(`Congress snapshot HTTP ${r.status}`);
        const d=await r.json();
        if(!politiciansSnapshotFresh(d)) throw new Error('Congress snapshot desactualizado');
        const trades=d.trades.map(normalizeCongressLive).filter(x=>x.ticker);
        M.congressLive=trades; M.congressLoaded=true; M.congressError='';
        attachCongressToStocks(trades);
        try{ localStorage.setItem(cacheKey,JSON.stringify({ts:Date.now(),trades})); }catch(_){}
        return trades;
      }catch(e){
        M.congressLive=[]; M.congressLoaded=true;
        M.congressError=e?.message||'Congress snapshot indisponível';
        return [];
      }finally{
        M.congressLoading=null;
      }
    })();

    const all=await M.congressLoading;
    return tk ? all.filter(x=>x.ticker.split('.')[0]===tk) : all;
  }

"""
s=s[:start]+new+s[end:]
if 'www.bargo.ai/free-apis/congress' in s or '/congress?' in s:
    raise SystemExit('legacy Congress network source remains in market.js')
if './data/politicians.json' not in s:
    raise SystemExit('canonical politicians snapshot not wired')
p.write_text(s)
print('market Congress live source replaced with canonical local snapshot')
