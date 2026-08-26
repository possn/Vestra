from pathlib import Path

p=Path('market.js')
s=p.read_text(encoding='utf-8')
old='''  function low52Stats(s){
    const hist=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const closes=hist.map(x=>n(x?.close)).filter(x=>x!=null&&x>0);
    const current=n(s?.current_price) ?? (closes.length?closes[closes.length-1]:null);
    if(!closes.length || current==null || current<=0) return null;
    const low=Math.min(...closes);
    const high=Math.max(...closes);
    if(!(low>0)) return null;
    const above=(current/low-1)*100;
    return {low,high,current,above};
  }
'''
new='''  function low52Stats(s){
    // The startup market index deliberately omits the full 1Y history. Use the
    // compact 52-week bounds there; once a dossier is hydrated the complete
    // history remains available and takes precedence.
    const hist=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const closes=hist.map(x=>n(x?.close)).filter(x=>x!=null&&x>0);
    const current=n(s?.current_price) ?? (closes.length?closes[closes.length-1]:null);
    const low=closes.length?Math.min(...closes):(n(s?.low52_price_low)??n(s?.fifty_two_week_low));
    const high=closes.length?Math.max(...closes):(n(s?.low52_price_high)??n(s?.fifty_two_week_high));
    if(current==null || current<=0 || low==null || low<=0) return null;
    const above=(current/low-1)*100;
    return {low,high:high??low,current,above};
  }
'''
if old not in s:
    raise SystemExit('expected low52Stats block not found; refusing unsafe patch')
if s.count(old)!=1:
    raise SystemExit(f'expected exactly one low52Stats block, found {s.count(old)}')
p.write_text(s.replace(old,new,1),encoding='utf-8')
