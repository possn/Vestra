from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    p=ROOT/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'anchor not found in {path}: {old[:120]}')
    p.write_text(s.replace(old,new,1))

# run.py — integrate low52 overlay before scanner and bump schema.
replace_once('scripts/run.py',
"from catalysts import assess as assess_catalysts\nfrom scanner import assess as assess_scanner",
"from catalysts import assess as assess_catalysts\nfrom low52_intelligence import assess as assess_low52_intelligence\nfrom scanner import assess as assess_scanner")
replace_once('scripts/run.py',
"        row.update(assess_catalysts(row))\n        row.update(assess_scanner(row))",
"        row.update(assess_catalysts(row))\n        row.update(assess_low52_intelligence(row))\n        row.update(assess_scanner(row))")
replace_once('scripts/run.py','"schema_version": 517','"schema_version": 518')

# scanner.py — let the dedicated low52 engine drive the two low strategies.
replace_once('scripts/scanner.py',
"    div_yield=_n(row.get(\"dividend_yield\")); div_cover=_n(row.get(\"dividend_fcf_coverage\")); low52=_low52(row); div_growth=_dividend_growth(row)\n    flags=set(row.get(\"risk_flags\") or []); safe_gate=gate in (\"clear\",\"watch\"); results={}",
"    div_yield=_n(row.get(\"dividend_yield\")); div_cover=_n(row.get(\"dividend_fcf_coverage\")); low52=_low52(row); div_growth=_dividend_growth(row)\n    low52_status=str(row.get(\"low52_status\") or \"\"); low52_score=_n(row.get(\"low52_score\")); low52_reasons=list(row.get(\"low52_reasons\") or [])\n    flags=set(row.get(\"risk_flags\") or []); safe_gate=gate in (\"clear\",\"watch\"); results={}")
replace_once('scripts/scanner.py',
"    if low52 and low52[\"above_pct\"]<=15 and safe_gate and (quality or 0)>=60 and (conf or 0)>=60 and (score or 0)>=58 and thesis!=\"down\" and (rev is None or rev>-0.12) and not ({\"material_dilution\",\"severe_dilution\"}&flags):\n        add(\"fallen_angels\",\"Fallen Angels\",[_clamp(100-low52[\"above_pct\"]*4),quality,conf,score],[f\"{max(0,low52['above_pct']):.1f}% acima do mínimo 52s\",f\"Qualidade {quality:.0f}/100\",f\"Confiança {conf:.0f}/100\",\"Sem deterioração estrutural dominante\"])\n    if low52 and low52[\"above_pct\"]<=5 and safe_gate and (quality or 0)>=60 and (conf or 0)>=60 and (score or 0)>=55 and (rev is None or rev>-0.15) and not ({\"material_dilution\",\"severe_dilution\",\"weak_quality\"}&flags):\n        add(\"lows_intact\",\"Mínimos 52s · fundamentos intactos\",[_clamp(100-low52[\"above_pct\"]*8),quality,conf,score],[f\"{max(0,low52['above_pct']):.1f}% acima do mínimo 52s\",f\"Qualidade {quality:.0f}/100\",f\"Confiança {conf:.0f}/100\",\"Risk Gate sem alerta alto/severo\"])",
"    if low52 and low52[\"above_pct\"]<=15 and low52_status in (\"opportunity\",\"watch\") and low52_score is not None:\n        add(\"fallen_angels\",\"Fallen Angels\",[low52_score,quality,conf,score],low52_reasons or [f\"{max(0,low52['above_pct']):.1f}% acima do mínimo 52s\",\"Sem deterioração estrutural dominante\"])\n    if low52 and low52[\"above_pct\"]<=5 and low52_status==\"opportunity\" and low52_score is not None:\n        add(\"lows_intact\",\"Mínimos 52s · fundamentos intactos\",[low52_score,quality,conf,score],low52_reasons or [f\"{max(0,low52['above_pct']):.1f}% acima do mínimo 52s\",\"Risk Gate sem alerta alto/severo\"])")

# market.js — richer lows classification.
replace_once('market.js',
"      const meta=`${dist.toFixed(1)}% acima do mínimo · mínimo ${money(stats.low,currency)}`;\n      return renderRow(s,meta);",
"      const status=txt(s.low52_status), label=txt(s.low52_label)||'Sem classificação', lowScore=n(s.low52_score);\n      const meta=`${dist.toFixed(1)}% acima do mínimo · ${label}${lowScore!=null?` · Low52 ${Math.round(lowScore)}/100`:''} · mínimo ${money(stats.low,currency)}`;\n      return renderRow(s,meta);")
replace_once('market.js',
"      .sort((a,b)=>a.stats.above-b.stats.above || (n(b.s.score)||0)-(n(a.s.score)||0));",
"      .sort((a,b)=>{const rank={opportunity:0,watch:1,uncertain:2,value_trap_risk:3,structural_risk:4,insufficient:5}; return (rank[txt(a.s.low52_status)]??9)-(rank[txt(b.s.low52_status)]??9)||(n(b.s.low52_score)||0)-(n(a.s.low52_score)||0)||a.stats.above-b.stats.above;});")
replace_once('market.js',
"<h3>Mínimos de 52 semanas</h3><p>Empresas até 5% acima do mínimo dos últimos 12 meses, ordenadas pela proximidade ao mínimo.</p>",
"<h3>Mínimos de 52 semanas</h3><p>Até 5% do mínimo, agora classificados por oportunidade potencial, queda saudável, value trap ou deterioração estrutural.</p>")

# Research Queue v6.3 — preserve state metadata, add checkpoint/note editor.
replace_once('market.js',
"    return {status:x.status||'new',snoozeUntil:Number(x.snoozeUntil||0),updatedAt:Number(x.updatedAt||0)};",
"    return {status:x.status||'new',snoozeUntil:Number(x.snoozeUntil||0),updatedAt:Number(x.updatedAt||0),checkpoint:txt(x.checkpoint),note:txt(x.note),checkpointAt:Number(x.checkpointAt||0)};")
replace_once('market.js',
"    all[key]={status,updatedAt:Date.now(),snoozeUntil:status==='snoozed'?Date.now()+7*86400000:0};",
"    const prev=all[key]||{}; all[key]={...prev,status,updatedAt:Date.now(),snoozeUntil:status==='snoozed'?Date.now()+7*86400000:0};")
insert_anchor="  function renderResearchQueue(review){\n"
insert_code="""  function saveResearchCheckpoint(ticker,checkpoint,note){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(); if(!key)return;
    const prev=all[key]||{};
    all[key]={...prev,checkpoint:txt(checkpoint),note:txt(note).slice(0,500),checkpointAt:Date.now(),updatedAt:Date.now()};
    saveResearchQueue(all);
  }
  function researchCheckpointEditor(ticker,state){
    const cp=txt(state?.checkpoint)||'';
    return `<div class="market-research-checkpoint" data-checkpoint-ticker="${esc(ticker)}"><select data-checkpoint-select><option value="" ${!cp?'selected':''}>Checkpoint…</option><option value="maintain" ${cp==='maintain'?'selected':''}>Mantém</option><option value="deteriorated" ${cp==='deteriorated'?'selected':''}>Deteriorou</option><option value="wait_earnings" ${cp==='wait_earnings'?'selected':''}>Aguardar earnings</option><option value="improving" ${cp==='improving'?'selected':''}>A melhorar</option><option value="exit_review" ${cp==='exit_review'?'selected':''}>Rever saída</option></select><input type="text" maxlength="500" data-checkpoint-note placeholder="Nota curta de research" value="${esc(state?.note||'')}"><button type="button" data-checkpoint-save>Guardar</button></div>`;
  }

"""
replace_once('market.js',insert_anchor,insert_code+insert_anchor)
replace_once('market.js',
"<div class=\"market-research-queue-actions\"><button type=\"button\" data-queue-status=\"in_review\">Em revisão</button><button type=\"button\" data-queue-status=\"reviewed\">Revisto</button><button type=\"button\" data-queue-status=\"snoozed\">Adiar 7d</button></div></div>`).join('')",
"<div class=\"market-research-queue-actions\"><button type=\"button\" data-queue-status=\"in_review\">Em revisão</button><button type=\"button\" data-queue-status=\"reviewed\">Revisto</button><button type=\"button\" data-queue-status=\"snoozed\">Adiar 7d</button></div>${state.status==='in_review'||state.checkpoint?researchCheckpointEditor(r.stock.ticker,state):''}</div>`).join('')")

# Event handler for checkpoint saves.
replace_once('market.js',
"  // v6.0.1 — Action Map summary acts as an immediate filter.\n",
"  // v6.3 — Thesis checkpoint + note for Research Queue.\n  document.addEventListener('click', e=>{\n    const btn=e.target.closest?.('[data-checkpoint-save]'); if(!btn)return;\n    const box=btn.closest('.market-research-checkpoint'); if(!box)return;\n    e.preventDefault(); e.stopPropagation();\n    saveResearchCheckpoint(box.dataset.checkpointTicker||'',box.querySelector('[data-checkpoint-select]')?.value||'',box.querySelector('[data-checkpoint-note]')?.value||'');\n    btn.textContent='Guardado'; setTimeout(()=>{btn.textContent='Guardar';},900);\n  });\n\n  // v6.0.1 — Action Map summary acts as an immediate filter.\n")

# CSS
p=ROOT/'market.css'; css=p.read_text(); css += """

/* v6.3 — Research checkpoint + richer lows */
.market-research-checkpoint{display:grid;grid-template-columns:150px minmax(0,1fr) auto;gap:7px;padding:8px 0 2px}.market-research-checkpoint select,.market-research-checkpoint input{min-width:0;border:1px solid var(--line);background:var(--card2);color:var(--text);border-radius:11px;padding:9px 10px;font:inherit;font-size:11px}.market-research-checkpoint button{border:0;border-radius:11px;background:var(--text);color:var(--card);font-weight:800;padding:9px 11px;cursor:pointer}@media(max-width:620px){.market-research-checkpoint{grid-template-columns:1fr auto}.market-research-checkpoint input{grid-column:1/-1;grid-row:2}}
"""; p.write_text(css)

# README top + cache bump.
p=ROOT/'README.md'; read=p.read_text(); p.write_text("""## Vestra v6.3 — Thesis Checkpoints & Low52 Intelligence

- Research Queue passa a guardar checkpoint da tese e uma nota curta por posição, localmente no dispositivo.
- Checkpoints: Mantém, Deteriorou, Aguardar earnings, A melhorar e Rever saída; não alteram Score Vestra nem a carteira.
- Novo motor específico para empresas perto dos mínimos de 52 semanas: combina qualidade, balanço, cash flow, confiança, valuation, expectativas, receita/margens, diluição, estrutura de capital e Risk Gate.
- Cada empresa perto do mínimo é classificada como Oportunidade potencial, Queda saudável / acompanhar, Indeterminado, Risco de value trap ou Deterioração estrutural.
- Fallen Angels e Mínimos intactos passam a consumir esta classificação em vez de apenas thresholds simples.
- Dataset schema: 518. PWA cache: `vestra-cache-v60`.

"""+read)

p=ROOT/'sw.js'; sw=p.read_text().replace('vestra-cache-v59','vestra-cache-v60'); p.write_text(sw)
