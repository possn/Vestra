from pathlib import Path
root=Path(__file__).resolve().parents[1]

p=root/'scripts/run.py'; s=p.read_text()
anchor='from peer_drawdown import assess_universe as assess_peer_drawdown\n'
if 'from recovery_confirmation import assess_universe as assess_recovery_confirmation' not in s:
    assert anchor in s
    s=s.replace(anchor,anchor+'from recovery_confirmation import assess_universe as assess_recovery_confirmation\n',1)
anchor2='    rows = assess_peer_drawdown(rows)\n\n    payload = {'
if 'rows = assess_recovery_confirmation(rows)' not in s:
    assert anchor2 in s
    s=s.replace(anchor2,'    rows = assess_peer_drawdown(rows)\n    rows = assess_recovery_confirmation(rows)\n\n    payload = {',1)
s=s.replace('"schema_version": 520','"schema_version": 521',1)
p.write_text(s)

p=root/'market.js'; s=p.read_text()
if 'function recoveryPanel(s)' not in s:
    marker='  function drawdownPanel(s){'
    assert marker in s
    fn='''  function recoveryPanel(s){\n    const status=txt(s.recovery_status), label=txt(s.recovery_label), score=n(s.recovery_score);\n    if(!status || status==='insufficient') return '';\n    const r20=n(s.recovery_return_20d_pct), r60=n(s.recovery_return_60d_pct);\n    const reasons=Array.isArray(s.recovery_reasons)?s.recovery_reasons:[];\n    const tone=(status==='confirmed'||status==='recovering')?'is-positive':(status==='failed'||status==='bounce_only')?'is-risk':'';\n    return `<div class="market-detail-card"><div class="market-perspective-head"><div><small>RECOVERY CONFIRMATION</small><h4>${esc(label||'Sem confirmação')}</h4></div><span class="market-data-age ${tone}">${score==null?'—':Math.round(score)+'/100'}</span></div><div class="market-mini-grid"><div><small>Preço 20d</small><strong>${r20==null?'—':`${r20>0?'+':''}${r20.toFixed(1)}%`}</strong></div><div><small>Preço 60d</small><strong>${r60==null?'—':`${r60>0?'+':''}${r60.toFixed(1)}%`}</strong></div><div><small>Confirmação preço</small><strong>${n(s.recovery_price_score)==null?'—':Math.round(n(s.recovery_price_score))+'/100'}</strong></div><div><small>Confirmação fundamental</small><strong>${n(s.recovery_fundamental_score)==null?'—':Math.round(n(s.recovery_fundamental_score))+'/100'}</strong></div></div>${reasons.length?`<p class="market-case-note">${reasons.slice(0,4).map(esc).join(' · ')}</p>`:''}<p class="market-case-note">Confirmação de recuperação combina preço recente e melhoria fundamental; não é sinal de entrada nem altera o Score Vestra.</p></div>`;\n  }\n\n'''
    s=s.replace(marker,fn+marker,1)
if '${recoveryPanel(s)}${drawdownPanel(s)}' not in s:
    anchor3='${drawdownPanel(s)}'
    assert anchor3 in s
    s=s.replace(anchor3,'${recoveryPanel(s)}${drawdownPanel(s)}',1)
old="const meta=[`${dist.toFixed(1)}% acima do mínimo`,label,lowScore!=null?`Low52 ${Math.round(lowScore)}/100`:'',cause,trendText].filter(Boolean).join(' · ');"
if 'recoveryLabel' not in s:
    assert old in s
    new="const recoveryLabel=txt(s.recovery_label), recoveryScore=n(s.recovery_score);\n      const meta=[`${dist.toFixed(1)}% acima do mínimo`,label,lowScore!=null?`Low52 ${Math.round(lowScore)}/100`:'',cause,trendText,recoveryLabel,recoveryScore!=null?`Recovery ${Math.round(recoveryScore)}/100`:'' ].filter(Boolean).join(' · ');"
    s=s.replace(old,new,1)
p.write_text(s)

p=root/'README.md'; s=p.read_text()
if not s.startswith('## Vestra v6.6'):
    s='''## Vestra v6.6 — Recovery Confirmation\n\n- Empresas em drawdown/mínimos passam a distinguir simples ressalto de recuperação apoiada por evidência.\n- Estados: Sem confirmação, Estabilização, Recuperação em curso, Recuperação confirmada, Ressalto sem confirmação e Falha de recuperação.\n- Cruza retornos 20/60 dias com expectativas, aceleração de receita, margens, tese, tendência da causa da queda e comportamento relativo ao setor.\n- Novo card Recovery Confirmation no dossier e contexto adicional em Mínimos 52s.\n- Não altera Score Vestra nem constitui sinal de entrada.\n- Dataset schema: 521. PWA cache: `vestra-cache-v63`.\n\n'''+s
p.write_text(s)

p=root/'sw.js'; s=p.read_text().replace('vestra-cache-v62','vestra-cache-v63'); p.write_text(s)
