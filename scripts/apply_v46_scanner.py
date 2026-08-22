from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def repl(path,old,new):
    p=ROOT/path; s=p.read_text(encoding='utf-8')
    if new in s: return
    if old not in s: raise RuntimeError(f'anchor missing {path}: {old[:100]!r}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

# Pipeline: scanner runs after thesis evolution so turnaround rules can use deltas.
repl('scripts/run.py','from earnings_intelligence import assess as assess_earnings_intelligence\n','from earnings_intelligence import assess as assess_earnings_intelligence\nfrom scanner import assess as assess_scanner\n')
repl('scripts/run.py','''        row.update(evolve_thesis(\n            row, prev_snapshot, prev_date,\n            d7_snapshot, d7_date, d30_snapshot, d30_date,\n        ))\n        rows.append(row)\n''','''        row.update(evolve_thesis(\n            row, prev_snapshot, prev_date,\n            d7_snapshot, d7_date, d30_snapshot, d30_date,\n        ))\n        row.update(assess_scanner(row))\n        rows.append(row)\n''')
repl('scripts/run.py','"schema_version": 515,','"schema_version": 516,')

# Market: scanner lives under More tools to preserve the frozen primary navigation.
repl('index.html','''<button class="market-tool-btn" data-market-tool="news">Notícias<small>Posições e pesquisa</small></button>\n''','''<button class="market-tool-btn" data-market-tool="news">Notícias<small>Posições e pesquisa</small></button>\n<button class="market-tool-btn" data-market-tool="scanner">Scanner Vestra<small>Estratégias inteligentes</small></button>\n''')

scanner_js=r'''
  const SCANNER_STRATEGIES=[
    ['qarp','QARP','Qualidade + valuation'],
    ['fallen_angels','Fallen Angels','Preço deprimido, tese intacta'],
    ['lows_intact','Mínimos intactos','52s sem red flags'],
    ['positive_revisions','Revisões +','Expectativas a melhorar'],
    ['insider_accumulation','Insiders','Compras open-market'],
    ['turnarounds','Turnarounds','Execução a recuperar'],
    ['dividend_growers','Dividend growers','Rendimento sustentável']
  ];
  function scannerResult(s,key){ return s?.scanner_results && typeof s.scanner_results==='object' ? s.scanner_results[key] : null; }
  function renderScanner(strategy='qarp'){
    const meta=SCANNER_STRATEGIES.find(x=>x[0]===strategy)||SCANNER_STRATEGIES[0];
    let rows=M.stocks.filter(s=>!isFund(s)&&scannerResult(s,meta[0]))
      .sort((a,b)=>(n(scannerResult(b,meta[0])?.score)||0)-(n(scannerResult(a,meta[0])?.score)||0));
    const total=rows.length; rows=rows.slice(0,30);
    const chips=SCANNER_STRATEGIES.map(([key,label])=>`<button class="market-chip ${key===meta[0]?'is-active':''}" data-scanner-strategy="${key}">${esc(label)}</button>`).join('');
    const body=rows.length?rows.map(s=>{
      const r=scannerResult(s,meta[0])||{}; const reasons=Array.isArray(r.reasons)?r.reasons:[];
      const line=[`Scanner ${Math.round(n(r.score)||0)}/100`,...reasons.slice(0,2)].join(' · ');
      return renderRow(s,line);
    }).join(''):`<div class="market-empty"><strong>Sem candidatos robustos neste momento.</strong><br><span>O filtro prefere não mostrar nada a aceitar empresas com evidência insuficiente ou Risk Gate elevado.</span></div>`;
    return `<div class="market-detail-head"><div><div class="market-kicker">SCANNER VESTRA</div><h2>${esc(meta[1])}</h2><p>${esc(meta[2])}. Estratégias independentes do core score, com filtros de confiança e risco.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-chipbar" style="margin-bottom:12px">${chips}</div><section class="market-section"><div class="market-section__head"><div><h3>Candidatos</h3><p>Ordenados pelo score específico desta estratégia.</p></div><span class="market-data-age">${total} ${total===1?'empresa':'empresas'}</span></div><div class="market-list">${body}</div></section>`;
  }
'''
repl('market.js','''  function renderPrimary(){\n''',scanner_js+'''\n  function renderPrimary(){\n''')
repl('market.js','''      if(tool==='news'){\n        const p=portfolioTickers(); const picks=[...p].map(t=>M.byTicker.get(t)).filter(Boolean).slice(0,12);\n        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">NOTÍCIAS</div><h2>Notícias das tuas posições</h2><p>Abre uma posição para ver o feed específico.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-list">${picks.length?picks.map(s=>renderRow(s,'Abrir notícias e dossier')).join(''):'<div class="market-empty">Sem posições reconhecidas.</div>'}</div>`;\n      }\n''','''      if(tool==='news'){\n        const p=portfolioTickers(); const picks=[...p].map(t=>M.byTicker.get(t)).filter(Boolean).slice(0,12);\n        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">NOTÍCIAS</div><h2>Notícias das tuas posições</h2><p>Abre uma posição para ver o feed específico.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-list">${picks.length?picks.map(s=>renderRow(s,'Abrir notícias e dossier')).join(''):'<div class="market-empty">Sem posições reconhecidas.</div>'}</div>`;\n      }\n      if(tool==='scanner') c.innerHTML=renderScanner('qarp');\n''')
repl('market.js','''    const tool=e.target.closest('[data-market-tool]'); if(tool) openTool(tool.dataset.marketTool);\n''','''    const strat=e.target.closest('[data-scanner-strategy]'); if(strat){ const c=$m('marketSheetContent'); if(c)c.innerHTML=renderScanner(strat.dataset.scannerStrategy); return; }\n    const tool=e.target.closest('[data-market-tool]'); if(tool) openTool(tool.dataset.marketTool);\n''')

# Release metadata.
p=ROOT/'README.md'; s=p.read_text(encoding='utf-8')
head='''## Vestra v4.6 — Intelligent Scanner\n\n- Novo Scanner Vestra em Mais ferramentas, sem alterar a navegação principal congelada.\n- Estratégias: QARP, Fallen Angels, Mínimos 52s com fundamentos intactos, Revisões positivas, Insider Accumulation, Turnarounds e Dividend Growers.\n- Cada estratégia tem score próprio 0–100 e razões auditáveis; não altera o core Score Vestra.\n- Confidence Engine e Risk Gate são filtros obrigatórios onde aplicável, reduzindo falling knives e falsos positivos de valuation.\n- O botão Mínimos 52s continua como pesquisa ampla; “Mínimos intactos” é a versão filtrada por qualidade, confiança, diluição e risco.\n- Layout visual global permanece congelado.\n- Dataset schema: 516. PWA cache: `vestra-cache-v39`.\n\n'''
if not s.startswith('## Vestra v4.6'): p.write_text(head+s,encoding='utf-8')
repl('sw.js','/* Vestra — Service Worker v4.5 */','/* Vestra — Service Worker v4.6 */')
repl('sw.js','const CACHE_NAME = "vestra-cache-v38";','const CACHE_NAME = "vestra-cache-v39";')
