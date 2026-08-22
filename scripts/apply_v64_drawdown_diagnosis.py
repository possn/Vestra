from pathlib import Path

root=Path(__file__).resolve().parents[1]

p=root/'scripts/run.py'
s=p.read_text()
anchor='from low52_intelligence import assess as assess_low52_intelligence\n'
if 'from drawdown_diagnosis import assess as assess_drawdown_diagnosis' not in s:
    assert anchor in s
    s=s.replace(anchor,anchor+'from drawdown_diagnosis import assess as assess_drawdown_diagnosis\n',1)
anchor2='        row.update(assess_low52_intelligence(row))\n        row.update(assess_scanner(row))\n'
if 'row.update(assess_drawdown_diagnosis(row))' not in s:
    assert anchor2 in s
    s=s.replace(anchor2,'        row.update(assess_low52_intelligence(row))\n        row.update(assess_drawdown_diagnosis(row))\n        row.update(assess_scanner(row))\n',1)
s=s.replace('"schema_version": 518','"schema_version": 519',1)
p.write_text(s)

p=root/'market.js'
s=p.read_text()
if 'function drawdownPanel(s)' not in s:
    marker='  function investmentCase(s){\n'
    assert marker in s
    fn=r'''  function drawdownPanel(s){
    const items=Array.isArray(s.drawdown_diagnosis)?s.drawdown_diagnosis:[];
    if(!items.length || txt(s.drawdown_diagnosis_status)==='not_material') return '';
    const trendLabel={improving:'a melhorar',deteriorating:'a piorar',stable:'estável'};
    const trendTone={improving:'is-positive',deteriorating:'is-risk',stable:''};
    const primary=items[0]||{};
    const mixed=txt(s.drawdown_diagnosis_status)==='mixed';
    const title=mixed?'Queda com causas mistas':(s.drawdown_primary_label||primary.label||'Causa não identificada');
    const dd=n(s.drawdown_from_high_pct);
    return `<div class="market-detail-card market-drawdown-panel"><div class="market-perspective-head"><div><small>PORQUE CAIU? · DIAGNÓSTICO</small><h4>${esc(title)}</h4></div><span class="market-data-age">${dd==null?'drawdown':`${dd.toFixed(0)}% vs máximo 52s`}</span></div><p class="market-case-note">Diagnóstico por evidência disponível; identifica drivers prováveis, não prova causalidade.</p><div class="market-drawdown-drivers">${items.slice(0,4).map((d,i)=>`<div class="market-drawdown-driver ${i===0?'is-primary':''}"><div><strong>${esc(d.label||d.key||'Driver')}</strong><small>${(d.evidence||[]).slice(0,2).map(esc).join(' · ')||'Evidência limitada'}</small></div><span><b>${Math.round(n(d.strength)||0)}</b><em class="${trendTone[txt(d.trend)]||''}">${esc(trendLabel[txt(d.trend)]||'estável')}</em></span></div>`).join('')}</div></div>`;
  }

'''
    s=s.replace(marker,fn+marker,1)
old="if(tab==='overview') body.innerHTML=`${changePanel(s)}${catalystPanel(s)}${investmentCase(s)}"
new="if(tab==='overview') body.innerHTML=`${changePanel(s)}${drawdownPanel(s)}${catalystPanel(s)}${investmentCase(s)}"
assert old in s
s=s.replace(old,new,1)
old_meta="      const status=txt(s.low52_status), label=txt(s.low52_label)||'Sem classificação', lowScore=n(s.low52_score);\n      const meta=`${dist.toFixed(1)}% acima do mínimo · ${label}${lowScore!=null?` · Low52 ${Math.round(lowScore)}/100`:''} · mínimo ${money(stats.low,currency)}`;"
new_meta="      const status=txt(s.low52_status), label=txt(s.low52_label)||'Sem classificação', lowScore=n(s.low52_score);\n      const cause=txt(s.drawdown_primary_label), trend=txt(s.drawdown_driver_trend);\n      const trendText=trend==='improving'?'causa a melhorar':trend==='deteriorating'?'causa a piorar':'';\n      const meta=[`${dist.toFixed(1)}% acima do mínimo`,label,lowScore!=null?`Low52 ${Math.round(lowScore)}/100`:'',cause,trendText].filter(Boolean).join(' · ');"
assert old_meta in s
s=s.replace(old_meta,new_meta,1)
p.write_text(s)

p=root/'market.css'
s=p.read_text()
if '.market-drawdown-drivers' not in s:
    s += r'''

/* v6.4 — Drawdown Diagnosis */
.market-drawdown-drivers{display:grid;gap:8px;margin-top:10px}
.market-drawdown-driver{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;border:1px solid var(--line);border-radius:14px;background:color-mix(in srgb,var(--paper) 92%,transparent)}
.market-drawdown-driver.is-primary{border-color:color-mix(in srgb,var(--ink) 28%,var(--line));background:color-mix(in srgb,var(--paper) 82%,var(--warm) 18%)}
.market-drawdown-driver>div{min-width:0;display:grid;gap:3px}.market-drawdown-driver strong{color:var(--ink);font-size:14px}.market-drawdown-driver small{color:var(--muted);line-height:1.35}
.market-drawdown-driver>span{display:grid;justify-items:end;gap:2px;flex:0 0 auto}.market-drawdown-driver b{font-size:17px;color:var(--ink)}.market-drawdown-driver em{font-style:normal;font-size:11px;color:var(--muted)}.market-drawdown-driver em.is-positive{color:var(--positive)}.market-drawdown-driver em.is-risk{color:var(--risk)}
'''
p.write_text(s)

p=root/'README.md'
s=p.read_text()
if not s.startswith('## Vestra v6.4'):
    s='''## Vestra v6.4 — Drawdown Diagnosis\n\n- Empresas com drawdown material passam a ter diagnóstico explícito do provável motor da queda: operação, expectativas, balanço/financiamento, diluição, compressão de múltiplos ou mercado/setor residual.\n- Cada driver tem intensidade 0–100, evidência curta e tendência: a melhorar, estável ou a piorar.\n- O diagnóstico aparece no dossier em “Porque caiu?” e também contextualiza a lista de Mínimos 52s.\n- Não prova causalidade e não altera o Score Vestra; é uma camada explicável de research.\n- Dataset schema: 519. PWA cache: `vestra-cache-v61`.\n\n'''+s
p.write_text(s)

p=root/'sw.js'
s=p.read_text().replace('vestra-cache-v60','vestra-cache-v61')
p.write_text(s)
