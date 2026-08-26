from pathlib import Path

P = Path('vestra-ux-v452.js')
s = P.read_text(encoding='utf-8')

start = s.find("  const n=v=>")
end = s.find("  const PORTFOLIO_KINDS=[")
assert start >= 0 and end > start, 'v452 opportunity block markers changed'
block = s[start:end]
for token in ("function loadStocks()", "function refineOpportunities()", "function oppScore(s)", "data/stocks.json"):
    assert token in block, token

s = s[:start] + s[end:]
s = s.replace("  function apply(){refineOpportunities();classifyPortfolioCards();}\n", "  function apply(){classifyPortfolioCards();}\n")
old_start = "  function start(){addStyle();loadStocks().then(()=>{apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});});}\n"
new_start = "  function start(){addStyle();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}\n"
assert old_start in s, 'v452 start marker changed'
s = s.replace(old_start, new_start)

for token in ("loadStocks", "refineOpportunities", "oppScore", "data/stocks.json"):
    assert token not in s, token
for token in ("classifyPortfolioCards", "jumpPortfolio", "PORTFOLIO_KINDS"):
    assert token in s, token

P.write_text(s, encoding='utf-8')
print('Removed superseded opportunity engine/fetch from v452; portfolio behavior retained.')
