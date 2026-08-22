from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]

# run.py
p=root/'scripts/run.py'; s=p.read_text()
anchor='from low52_intelligence import assess as assess_low52_intelligence\n'
if 'from peer_drawdown import assess_universe as assess_peer_drawdown' not in s:
    assert anchor in s
    s=s.replace(anchor,anchor+'from peer_drawdown import assess_universe as assess_peer_drawdown\n',1)
if 'rows = assess_peer_drawdown(rows)' not in s:
    marker='    payload = {\n'
    assert marker in s
    s=s.replace(marker,'    rows = assess_peer_drawdown(rows)\n\n'+marker,1)
s=s.replace('"schema_version": 519','"schema_version": 520',1)
p.write_text(s)

# app.js — rankings must respect sign, not absolute magnitude
p=root/'app.js'; s=p.read_text()
old='var sorted = items.slice().sort(function(a,b){ return Math.abs(valFn(b))-Math.abs(valFn(a)); });'
assert old in s
s=s.replace(old,'var sorted = items.slice().sort(function(a,b){ return valFn(b)-valFn(a); });',1)
old_block='''  var gainers = allAssets.filter(function(a){return parseNum(a.costBasis)>50;});\n  var secGainAbs = rankSection("Maiores ganhos (€)", gainers, gainAbs, function(a,v){return fmtE(v);}, function(a,v){return clr(v);}, "📈");\n  var gainersReal = gainers.filter(function(a){return parseNum(a.value)>=parseNum(a.costBasis)*0.1 && parseNum(a.value)>20;});\n  var secGainPct = rankSection("Maiores ganhos (%)", gainersReal, gainPct, function(a,v){return fmtP(v);}, function(a,v){return clr(v);}, "🚀");\n  var losers = gainersReal.filter(function(a){return gainPct(a)<0;});'''
new_block='''  var costed = allAssets.filter(function(a){return parseNum(a.costBasis)>50;});\n  var validPerformance = costed.filter(function(a){return parseNum(a.value)>=parseNum(a.costBasis)*0.1 && parseNum(a.value)>20;});\n  var gainersAbs = validPerformance.filter(function(a){return gainAbs(a)>0.005;});\n  var gainersPct = validPerformance.filter(function(a){return gainPct(a)>0.005;});\n  var secGainAbs = rankSection("Maiores ganhos (€)", gainersAbs, gainAbs, function(a,v){return fmtE(v);}, function(a,v){return clr(v);}, "📈");\n  var secGainPct = rankSection("Maiores ganhos (%)", gainersPct, gainPct, function(a,v){return fmtP(v);}, function(a,v){return clr(v);}, "🚀");\n  var losers = validPerformance.filter(function(a){return gainPct(a)<-0.005;});'''
assert old_block in s
s=s.replace(old_block,new_block,1)
# bump SW registration query to force app shell refresh
s=s.replace('sw.js?v=20260509v61','sw.js?v=20260509v62',1)
p.write_text(s)

# market.js — expose sector-relative context in lows and dossier
p=root/'market.js'; s=p.read_text()
old="const meta=[`${dist.toFixed(1)}% acima do mínimo`,lowLabel,cause,trendText].filter(Boolean).join(' · ');"
if old in s:
    new="const peer=txt(s.sector_relative_drawdown_label); const rel=n(s.sector_relative_return_1y_pct);\n      const meta=[`${dist.toFixed(1)}% acima do mínimo`,lowLabel,cause,trendText,peer,rel!=null?`vs setor ${rel>0?'+':''}${rel.toFixed(0)} pp`:'' ].filter(Boolean).join(' · ');"
    s=s.replace(old,new,1)
# add peer context to drawdown panel note
old_note='<p class="market-case-note">Diagnóstico por evidência disponível; identifica drivers prováveis, não prova causalidade.</p>'
if old_note in s:
    new_note='<p class="market-case-note">Diagnóstico por evidência disponível; identifica drivers prováveis, não prova causalidade.</p>${txt(s.sector_relative_drawdown_label)?`<p class="market-case-note"><strong>${esc(s.sector_relative_drawdown_label)}</strong>${n(s.sector_relative_return_1y_pct)!=null?` · ${n(s.sector_relative_return_1y_pct)>0?\'+\':\'\'}${n(s.sector_relative_return_1y_pct).toFixed(1)} pp vs mediana do setor · ${n(s.sector_relative_peer_count)||0} pares`:\'\'}</p>`:\'\'}'
    s=s.replace(old_note,new_note,1)
p.write_text(s)

# README
p=root/'README.md'; s=p.read_text()
if not s.startswith('## Vestra v6.5'):
    intro='''## Vestra v6.5 — Sector-relative Drawdown & Flow Ranking Repair\n\n- Corrige os rankings de Fluxos: Maiores ganhos (€/% ) mostram apenas ganhos positivos; perdas e zeros deixam de contaminar o ranking.\n- A ordenação dos rankings deixa de usar valor absoluto, evitando que uma grande perda apareça como maior ganho.\n- Novo contexto empresa vs setor: retorno 1 ano de cada empresa comparado com a mediana de pelo menos 4 pares do mesmo setor.\n- Classifica a queda como sobretudo específica da empresa, pior que o setor, próxima do setor ou melhor que o setor.\n- Mínimos 52s e o card “Porque caiu?” passam a mostrar esta comparação; não altera Score Vestra.\n- Dataset schema: 520. PWA cache: `vestra-cache-v62`.\n\n'''
    s=intro+s
p.write_text(s)

# sw.js
p=root/'sw.js'; s=p.read_text().replace('vestra-cache-v61','vestra-cache-v62'); p.write_text(s)
