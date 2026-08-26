from pathlib import Path

p=Path('politicians.js')
s=p.read_text()
old="""      if(!d||!Array.isArray(d.trades)||!Array.isArray(d.members))throw new Error('Feed político inválido');
      recentTrades=d.trades.map"""
new="""      if(!d||Number(d.schema_version||0)<2||!Array.isArray(d.trades)||!Array.isArray(d.members))throw new Error('Feed político inválido ou antigo');
      const newest=t(d.newest_disclosure||d.source_last_updated);
      const newestMs=newest?new Date(newest+'T00:00:00Z').valueOf():NaN;
      const ageDays=Number.isFinite(newestMs)?Math.floor((Date.now()-newestMs)/86400000):9999;
      if(ageDays>60)throw new Error(`Dados políticos desactualizados · último filing ${newest||'desconhecido'}`);
      recentTrades=d.trades.map"""
if old not in s: raise SystemExit('freshness anchor not found')
s=s.replace(old,new,1)
old2="""    root.innerHTML=`<section class=\"market-section politicians-section\"><div class=\"market-section__head\"><div><h3>Políticos</h3><p>Divulgações STOCK Act do Congresso dos EUA · House + Senate.</p></div>"""
new2="""    const coverage=(feedMeta.coverage_chambers||[]).filter(Boolean).join(' + ')||'Congresso dos EUA';
    root.innerHTML=`<section class=\"market-section politicians-section\"><div class=\"market-section__head\"><div><h3>Políticos</h3><p>Divulgações STOCK Act · ${esc(coverage)}.</p></div>"""
if old2 not in s: raise SystemExit('coverage anchor not found')
s=s.replace(old2,new2,1)
p.write_text(s)
