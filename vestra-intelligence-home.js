/* Vestra Intelligence Home — default shell with explicit legacy rollback. */
(() => {
  'use strict';
  const params = new URLSearchParams(window.location.search);
  const enabled = params.get('vestra2') !== '0';
  if (!enabled) return;

  async function showCoverage(host) {
    const label = host.querySelector('[data-vestra-coverage]');
    const evidence = host.querySelector('[data-vestra-model-evidence]');
    if (!label) return;
    label.textContent = 'A verificar cobertura dos dados publicados…';
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      let response;
      try { response = await fetch('./data/coverage_guard.json', {cache:'no-store', signal:controller.signal}); }
      finally { clearTimeout(timeout); }
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const guard = await response.json();
      const date = Date.parse(guard?.generated_at);
      const rows = guard?.rows_checked;
      const violations = guard?.violation_count;
      if (!Number.isFinite(date) || date > Date.now() + 300000 ||
          !Number.isInteger(rows) || rows < 0 ||
          !Number.isInteger(violations) || violations < 0 ||
          typeof guard?.ok !== 'boolean') throw new Error('Dados incompletos');
      const ageHours = (Date.now() - date) / 3600000;
      const fresh = ageHours >= 0 && ageHours <= 36;
      const valid = guard.ok === true && violations === 0;
      if (evidence) {
        evidence.dataset.status = valid && fresh && rows > 0 ? 'observed' : 'stale';
        evidence.textContent = 'Model Evidence · integridade ' + (valid && fresh && rows > 0 ? 'verificada' : 'não confirmada') +
          ' · validação preditiva e fora da amostra não demonstrada neste relatório';
      }
      label.dataset.status = !valid ? 'bad' : fresh ? 'observed' : 'stale';
      const timestamp = new Date(date).toLocaleString('pt-PT');
      label.textContent = 'Cobertura publicada · ' + rows.toLocaleString('pt-PT') +
        ' ativos verificados · ' + violations + ' violações · ' +
        (valid ? (fresh ? 'verificada' : 'relatório antigo') : 'atenção') +
        ' · ' + timestamp + ' · Fonte: coverage_guard.json';
    } catch (_) {
      if (evidence) {
        evidence.dataset.status = 'missing';
        evidence.textContent = 'Model Evidence · integridade e validação preditiva não verificadas';
      }
      label.dataset.status = 'missing';
      label.textContent = 'Cobertura publicada indisponível · sem confirmação de integridade';
    }
  }

  async function showProspectiveValidation(host) {
    const output = host.querySelector('[data-vestra-prospective-evidence]');
    if (!output) return;
    output.dataset.status = 'missing';
    output.textContent = 'Validação prospetiva · a verificar histórico publicado…';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    async function readReport(path) {
      const response = await fetch(path, {cache:'no-store', signal:controller.signal});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }
    let results;
    try {
      results = await Promise.allSettled([
        readReport('./data/score_validation_report.json'),
        readReport('./data/opportunity_validation_report.json')
      ]);
    } finally { clearTimeout(timeout); }
    const score = results[0].status === 'fulfilled' ? results[0].value : null;
    const opportunity = results[1].status === 'fulfilled' ? results[1].value : null;
    const scoreTime = Date.parse(score?.generated_at);
    const validThrough = Date.parse(score?.freshness?.valid_through);
    const scoreFresh = Number.isFinite(scoreTime) && Number.isFinite(validThrough) &&
      scoreTime <= Date.now() + 300000 && Date.now() <= validThrough;
    const h = score?.horizons?.['28'];
    const n = h?.n, cohorts = h?.cohort_count, ic = h?.rank_information_coefficient;
    const scoreValid = scoreFresh && score?.schema_version === 5 &&
      Number.isInteger(n) && n >= 0 && Number.isInteger(cohorts) && cohorts >= 0 &&
      (ic === null || (typeof ic === 'number' && Number.isFinite(ic)));
    const oppTime = Date.parse(opportunity?.generated_at);
    const oppFresh = Number.isFinite(oppTime) && oppTime <= Date.now() + 300000 &&
      Date.now() - oppTime <= 36 * 3600000;
    const oppN = opportunity?.horizons?.['28']?.n;
    const oppValid = oppFresh && opportunity?.schema_version === 1 &&
      Number.isInteger(oppN) && oppN >= 0;
    const scoreText = scoreValid
      ? 'Score 28d: ' + n.toLocaleString('pt-PT') + ' observações em ' +
        cohorts + ' coortes · Rank IC ' + (ic == null ? 'indisponível' : ic.toFixed(3)) +
        ' · ' + (cohorts < 5 ? 'evidência temporal insuficiente' : 'evidência observacional')
      : 'Score: relatório indisponível ou desatualizado';
    const oppText = oppValid
      ? 'Oportunidades 28d: ' + oppN.toLocaleString('pt-PT') +
        ' resultados · ' + (oppN === 0 ? 'a recolher evidência' : 'evidência observacional')
      : 'Oportunidades: relatório indisponível ou desatualizado';
    output.dataset.status = scoreValid && oppValid && cohorts >= 5 && oppN > 0 ? 'observed'
      : scoreValid || oppValid ? 'stale' : 'missing';
    output.textContent = 'Validação prospetiva · ' + scoreText + ' · ' + oppText +
      ' · Fonte: relatórios prospetivos independentes';
    const panel = host.querySelector('[data-vestra-horizon-ledger]');
    if (panel) {
      const reportSummary = (report, valid, key) => {
        if (!valid) return key + ': indisponível ou desatualizado';
        return [28, 84, 168].map(days => {
          const row = report?.horizons?.[String(days)];
          const count = row?.n;
          const groups = row?.cohort_count;
          const rank = row?.rank_information_coefficient;
          if (!Number.isInteger(count) || count < 0 ||
              !Number.isInteger(groups) || groups < 0 ||
              !(rank == null || (typeof rank === 'number' && Number.isFinite(rank))))
            return days + 'd: dados não verificados';
          return days + 'd: ' + count.toLocaleString('pt-PT') +
            ' resultados / ' + groups + ' coortes' +
            (rank == null ? '' : ' / Rank IC ' + rank.toFixed(3)) +
            (groups < 5 ? ' · amostra temporal insuficiente' : ' · observacional') +
            (Number.isInteger(row?.positive_ic_cohorts) &&
              row.positive_ic_cohorts >= 0 && row.positive_ic_cohorts <= groups && groups > 0
                ? ' · IC positivo em ' + row.positive_ic_cohorts + '/' + groups + ' coortes'
                : '') +
            (typeof row?.median_cohort_rank_ic === 'number' &&
              Number.isFinite(row.median_cohort_rank_ic)
                ? ' · IC mediano ' + row.median_cohort_rank_ic.toFixed(3)
                : '');
        }).join('  |  ');
      };
      // Editorial lines remain text-only: no untrusted report HTML enters the DOM.
      panel.style.whiteSpace = 'pre-line';
      panel.setAttribute('aria-live', 'polite');
      panel.textContent = 'VESTRA · EVIDÊNCIA DOS MODELOS\n' +
        'Score — ' + reportSummary(score, scoreValid, 'Score') +
        '\nOportunidades — ' + reportSummary(opportunity, oppValid, 'Oportunidades') +
        '\nLeitura: observações por ativo não equivalem a coortes independentes. ' +
        'A consistência observada não comprova capacidade preditiva futura.';
      panel.dataset.status = scoreValid || oppValid ? 'observed' : 'missing';
      // Historical cohort points only: no reconstructed, projected or simulated series.
      const trend = host.querySelector('[data-vestra-cohort-trend]');
      if (trend) {
        const rows = scoreValid && Array.isArray(score?.horizons?.['28']?.cohorts)
          ? score.horizons['28'].cohorts.filter(c =>
              /^\d{4}-\d{2}-\d{2}$/.test(c?.cohort_date || '') &&
              Number.isFinite(c?.rank_information_coefficient) &&
              Number.isInteger(c?.n) && c.n > 0).slice(-12) : [];
        trend.replaceChildren();
        trend.dataset.status = rows.length ? 'observed' : 'missing';
        const heading = document.createElement('strong');
        heading.textContent = 'Score · evolução do Rank IC por coorte (28 dias)';
        trend.appendChild(heading);
        if (!rows.length) {
          const missing = document.createElement('p');
          missing.textContent = 'Histórico de coortes não disponível ou relatório desatualizado.';
          trend.appendChild(missing);
        } else {
          const sorted = rows.slice().sort((a, b) => a.cohort_date.localeCompare(b.cohort_date));
          const list = document.createElement('div');
          list.setAttribute('role', 'list');
          for (const row of sorted) {
            const item = document.createElement('div');
            item.setAttribute('role', 'listitem');
            item.style.cssText = 'display:grid;grid-template-columns:6.5rem 1fr 4.5rem;align-items:center;gap:.6rem;padding:.25rem 0';
            const date = document.createElement('span');
            date.textContent = row.cohort_date;
            const rail = document.createElement('div');
            rail.style.cssText = 'background:rgba(128,128,128,.14);height:.5rem;border-radius:99px;overflow:hidden';
            // Zero is the centre: negative correlations extend left, positive right.
            rail.style.position = 'relative';
            const zero = document.createElement('span');
            zero.style.cssText = 'position:absolute;left:50%;top:0;bottom:0;border-left:1px solid currentColor;opacity:.6';
            rail.appendChild(zero);
            const bar = document.createElement('div');
            const magnitude = Math.min(50, Math.abs(row.rank_information_coefficient) * 50);
            bar.style.cssText = 'position:absolute;top:0;bottom:0;background:currentColor;opacity:.65';
            bar.style.left = row.rank_information_coefficient < 0 ? (50 - magnitude) + '%' : '50%';
            bar.style.width = magnitude + '%';
            rail.appendChild(bar);
            const value = document.createElement('span');
            value.textContent = (row.rank_information_coefficient > 0 ? '+' : '') +
              row.rank_information_coefficient.toFixed(3);
            value.style.textAlign = 'right';
            item.append(date, rail, value);
            list.appendChild(item);
          }
          trend.appendChild(list);
          const foot = document.createElement('small');
          foot.textContent = sorted.length + ' coortes observadas · zero ao centro, IC negativo à esquerda e positivo à direita; ' +
            'zero ao centro, IC negativo à esquerda e positivo à direita · não é uma previsão.';
          trend.appendChild(foot);
        }
      }

    }
  }

  function syncExistingBarometer(host) {
    const output = host.querySelector('[data-vestra-market-status]');
    if (!output) return;
    const barometer = document.getElementById('vestraMarketSentimentCard');
    const score = barometer?.querySelector('.dms-score');
    const label = barometer?.querySelector('.dms-label');
    const raw = score?.textContent?.trim() || '';
    const value = Number.parseInt(raw, 10);
    if (!barometer || !score || !Number.isInteger(value) || value < 0 || value > 100 || !label?.textContent?.trim()) {
      output.dataset.status = 'missing';
      output.textContent = 'Barómetro indisponível · consultar a secção de mercado';
      return;
    }
    output.dataset.status = 'observed';
    output.textContent = 'Barómetro existente · ' + value + '/100 · ' +
      label.textContent.trim() + ' · Fonte: Vestra Market Sentiment (proxy de preço, não breadth real)';
  }

  function syncPortfolioEvidence(host) {
    const output = host.querySelector('[data-vestra-portfolio-evidence]');
    if (!output) return;
    const api = window.VestraDashboardPortfolioConcentration;
    try {
      if (!api || typeof api.marketHoldings !== 'function' ||
          typeof api.concentrationSnapshot !== 'function') throw new Error('motor indisponível');
      const snapshot = api.concentrationSnapshot(api.marketHoldings());
      if (!snapshot || !Number.isInteger(snapshot.count) || snapshot.count <= 0 ||
          !Number.isFinite(snapshot.top3) || snapshot.top3 < 0 || snapshot.top3 > 1)
        throw new Error('cobertura insuficiente');
      output.dataset.status = 'observed';
      // Do not expose personal portfolio values in the dashboard preview.
      output.textContent = 'Carteira · concentração mensurável em ' +
        snapshot.count + ' posições de mercado · Rever pesos e sobreposição no módulo Carteira · Fonte: motor de concentração existente';
    } catch (_) {
      output.dataset.status = 'missing';
      output.textContent = 'Carteira · concentração não confirmada · abrir Carteira para verificar';
    }
  }


  // Session-only snapshot: never persisted across reloads or users.
  // Derived exclusively from the canonical rendered Decision Center.
  let lastDecision = null;
  // Each pulse reading is source-backed; never claim a live reading from stale data.
  let pulseLastFetch=0;
  let pulseInFlight=null;
  function refreshLivePulse(host,force=false){
    if(pulseInFlight) return pulseInFlight;
    if(!force && Date.now()-pulseLastFetch < 15*60*1000) return Promise.resolve();
    pulseLastFetch=Date.now();
    const set=(key,value,age)=>{
      const label=host.querySelector('[data-vi-pulse-'+key+']');
      const detail=host.querySelector('[data-vi-pulse-'+key+'-age]');
      if(label) label.textContent=value;
      if(detail) detail.textContent=age;
    };
    const get=async url=>{
      const controller=new AbortController();
      const deadline=setTimeout(()=>controller.abort(),5000);
      try{const r=await fetch(url,{cache:'no-store',signal:controller.signal});if(!r.ok)throw Error('HTTP '+r.status);return await r.json();}
      catch(_){return null;}finally{clearTimeout(deadline);}
    };
    pulseInFlight=Promise.all([
      get('./data/cnn-fear-greed.json'),get('./data/aaii-sentiment.json'),get('./data/coverage_guard.json')
    ]).then(([cnn,aaii,guard])=>{
      const now=Date.now();
      const cnnTime=Date.parse(cnn?.timestamp);
      if(Number.isFinite(cnn?.score)&&Number.isFinite(cnnTime)&&cnnTime<=now+3600000&&now-cnnTime<72*3600000)
        set('cnn',String(Math.round(cnn.score))+'/100','CNN · '+new Date(cnnTime).toLocaleDateString('pt-PT'));
      else set('cnn','—','CNN · dados por confirmar');
      const week=aaii?.weeks?.[0],weekTime=Date.parse(String(week?.date||'')+'T00:00:00Z');
      const bull=Number(week?.bullish),bear=Number(week?.bearish),neutral=Number(week?.neutral);
      if(Number.isFinite(weekTime)&&now-weekTime<=9*86400000&&now>=weekTime&&
         [bull,bear,neutral].every(Number.isFinite)&&Math.abs(bull+bear+neutral-100)<1){
        const spread=bull-bear;
        set('aaii',(spread>0?'+':'')+spread.toFixed(1).replace('.',',')+' pp','AAII · '+new Date(weekTime).toLocaleDateString('pt-PT'));
      }else set('aaii','—','AAII · semana não validada');
      const generated=Date.parse(guard?.generated_at),count=Number(guard?.rows_checked),violations=Number(guard?.violation_count);
      if(guard?.ok===true&&Number.isFinite(generated)&&now>=generated&&now-generated<48*3600000&&Number.isInteger(count)&&count>0&&violations===0)
        set('coverage',count.toLocaleString('pt-PT'),'Verificados · 0 violações');
      else set('coverage','—','Cobertura sem confirmação recente');
    }).finally(()=>{pulseInFlight=null;});
    return pulseInFlight;
  }

  async function showPrebreakoutSpotlight(host) {
    let panel = host.querySelector('[data-vi-prebreakout-spotlight]');
    if (!panel) {
      panel = document.createElement('section');
      panel.dataset.viPrebreakoutSpotlight = '1';
      panel.setAttribute('aria-label', 'Ação em vigilância pre-breakout');
      panel.style.cssText = 'margin:.7rem 0 1rem;color:inherit';
      host.prepend(panel);
    }
    // The Home spotlight uses published scanner measurements, never a fabricated price sparkline.
    panel.classList.add('vi-pb-card');
    const element = (tag, cls, value) => {
      const node=document.createElement(tag);
      if(cls) node.className=cls;
      if(value!==undefined) node.textContent=String(value);
      return node;
    };
    const render = (title, detail, evidence, active, pick=null, qualified=false) => {
      panel.replaceChildren();
      const top=element('div','vi-pb-top');
      top.append(element('p','vi-pb-eyebrow','RADAR PRÉ-BREAKOUT'),
        element('span','vi-pb-status', qualified?'Sinal a investigar':'Em vigilância'));
      top.querySelector('.vi-pb-status').prepend(element('span','vi-pb-dot'));
      panel.append(top);
      const grid=element('div','vi-pb-grid');
      const main=element('div','vi-pb-main');
      if(pick){
        const identity=element('div','vi-pb-id');
        identity.append(element('span','vi-pb-monogram',pick.ticker.slice(0,2)),element('div','vi-pb-name'));
        identity.lastChild.append(element('div','vi-pb-ticker',pick.ticker),element('div','vi-pb-sub',pick.stage==='pré-breakout'?'Pré-breakout em observação':'Base em compressão'));
        main.append(identity);
      }
      main.append(element('h3','vi-pb-heading',title),element('p','vi-pb-detail',detail));
      grid.append(main);
      if(pick && Number.isFinite(pick.score)){
        const aside=element('div','vi-pb-aside');
        const ring=element('div','vi-pb-ring');
        ring.style.setProperty('--val',Math.max(0,Math.min(100,pick.score)));
        const number=element('div','vi-pb-number',Math.round(pick.score));
        number.append(element('small','', '/100'));
        ring.append(number);
        aside.append(ring,element('p','vi-pb-score-label','SCORE TÉCNICO'));
        grid.append(aside);
      }
      panel.append(grid);
      if(pick){
        const metrics=element('div','vi-pb-metrics');
        const addMetric=(label,value,width)=>{
          const item=element('div','vi-pb-metric');
          item.append(element('p','vi-pb-metric-title',label),element('p','vi-pb-metric-value',value));
          const track=element('div','vi-pb-track');
          const bar=element('span');
          bar.style.width=Math.max(0,Math.min(100,width))+'%';
          track.append(bar);item.append(track);metrics.append(item);
        };
        // Honest miniature chart: current base width versus prior width, not invented OHLCV.
        if(Number.isFinite(pick.widthPct)&&Number.isFinite(pick.priorWidthPct)&&pick.priorWidthPct>0){
          const ratio=pick.widthPct/pick.priorWidthPct;
          addMetric('Largura da base · antes',pick.priorWidthPct.toFixed(1).replace('.',',')+'%',100);
          addMetric('Largura da base · agora',pick.widthPct.toFixed(1).replace('.',',')+'%',ratio*100);
        } else if(Number.isFinite(pick.distancePct)){
          addMetric('Distância à resistência',pick.distancePct.toFixed(2).replace('.',',')+'%',Math.max(0,100-pick.distancePct*12.5));
        }
        if(metrics.childElementCount)panel.append(metrics);
      }
      panel.append(element('p','vi-pb-foot',evidence));
      if(active && pick?.ticker){
        const action=element('button','vi-pb-action','Investigar no Mercado →');
        action.type='button';
        action.dataset.vestraGo='market';
        action.dataset.vestraTicker=pick.ticker;
        action.setAttribute('aria-label','Investigar '+pick.ticker+' no Mercado');
        panel.append(action);
      }
    };
    render('A verificar o radar…', 'A consultar os dados técnicos publicados.', '', false);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      let response;
      try { response = await fetch('./data/prebreakout-signals.json', {cache:'no-store',signal:controller.signal}); }
      finally { clearTimeout(timeout); }
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const feed = await response.json();
      const stamp = Date.parse(feed?.generated_at);
      const hours = (Date.now()-stamp)/3600000;
      const fresh = feed?.schema === 'vestra_prebreakout_v1' &&
        Number.isFinite(stamp) && hours >= 0 && hours <= 72 &&
        Number.isInteger(feed.attempted) && feed.attempted > 0 &&
        Number.isInteger(feed.with_ohlcv) && feed.with_ohlcv > 0 &&
        Array.isArray(feed.signals);
      if (!fresh) throw new Error('Feed antigo ou incompleto');
      const rows = feed.signals.filter(row => {
        const bar = Date.parse(String(row?.date || '')+'T23:59:59Z');
        return row?.source === 'yahoo:daily_ohlcv' &&
          ['pré-breakout','compressão'].includes(row.stage) &&
          typeof row.ticker === 'string' && /^[A-Z0-9.\\-]{1,16}$/.test(row.ticker) &&
          Number.isFinite(bar) && bar <= Date.now()+86400000 && Date.now()-bar <= 7*86400000 &&
          Number.isFinite(row.score) && row.score>=0 && row.score<=100 &&
          Number.isFinite(row.distancePct) && row.distancePct>=0 && row.distancePct<=8 &&
          row.breakoutExtensionPct <= 0;
      });
      const qualified = rows.filter(row => row.stage === 'pré-breakout' && row.volumeDry === true)
        .sort((a,b) => b.score-a.score || a.distancePct-b.distancePct || a.ticker.localeCompare(b.ticker));
      const count = feed.with_ohlcv+'/'+feed.attempted;
      const source = 'OHLCV Yahoo · '+count+' títulos com dados nesta execução · '+new Date(stamp).toLocaleString('pt-PT')+' · Score técnico, não probabilidade';
      // New feeds publish a canonical, quality-ranked focus from the backend.
      // Never silently replace a deliberate abstention with the legacy score leader.
      // Older feeds without daily_focus keep the original fallback.
      const focus = feed.daily_focus;
      const hasCanonicalFocus = focus && typeof focus === 'object';
      const canonicalPick = hasCanonicalFocus && focus.status === 'research_candidate'
        ? qualified.find(row => row.ticker === focus.ticker &&
            row.date === focus.signal_date &&
            row.distancePct <= 4 && row.vcpConfirmed === true &&
            row.source === 'yahoo:daily_ohlcv') : null;
      const pick = hasCanonicalFocus ? canonicalPick : qualified[0];
      if (pick) {
        render(pick.ticker+' · Próximo do pivot',
          'Score técnico '+Math.round(pick.score)+'/100 · '+pick.distancePct.toFixed(2).replace('.',',')+
          '% abaixo da resistência · volume a secar comprovado. Investigar tese, risco e liquidez antes de qualquer decisão.',
          source+' · Melhor sinal da amostra analisada, não de todo o mercado.', true, pick, true);
      } else if (rows.length) {
        const watch = rows.sort((a,b)=>b.score-a.score || a.ticker.localeCompare(b.ticker))[0];
        render('Sem pré-breakout qualificado hoje',
          'Base em compressão. Ainda sem confirmação completa; não é uma oportunidade antecipatória validada.',
          source+' · Vigilância, não recomendação.',true,watch,false);
      } else {
        render('Nenhum setup elegível', 'O radar publicado não encontrou candidatos válidos nesta amostra.',
          source+' · Não inferir ausência de oportunidades no mercado inteiro.',true);
      }
    } catch (_) {
      render('Radar indisponível ou desatualizado',
        'Sem dados recentes e verificáveis, não é possível selecionar uma ação do dia.',
        'Sem sinais fabricados · consultar o módulo Mercado.',true);
    }
  }

  function syncDecisionCenter(host) {
    const output = host.querySelector('[data-vestra-decision-state]');
    if (!output) return;
    const sheet = document.getElementById('marketSheet');
    const center = sheet?.dataset.tool === 'portfolio'
      ? sheet.querySelector('.market-decision-center[data-vpu-state]') : null;
    const state = center?.dataset.vpuState || '';
    const rawCoverage = center?.dataset.vpuCoverage;
    const coverage = rawCoverage === undefined || rawCoverage === '' ? NaN : Number(rawCoverage);
    const known = ['Rever', 'Atenção', 'Acompanhar', 'Dados parciais', 'Estável'];
    // Do not convert an absent/invalid coverage to zero or a healthy decision.
    if (center && known.includes(state) && Number.isFinite(coverage) &&
        coverage >= 0 && coverage <= 100) {
      lastDecision = {state, coverage, observedAt: Date.now()};
    }
    const snapshot = lastDecision;
    const currentReading = Boolean(center && known.includes(state) && Number.isFinite(coverage) &&
      coverage >= 0 && coverage <= 100);
    // Do not silently present an old diagnosis as current.
    const age = snapshot ? Date.now() - snapshot.observedAt : Infinity;
    if (!snapshot || age < 0 || age > 15 * 60 * 1000) {
      lastDecision = null;
      output.dataset.status = 'missing';
      output.textContent = 'Decision Center · sem leitura verificada nesta sessão · abrir análise da Carteira';
      return;
    }
    // A historical observation is never a live clearance to invest.
    output.dataset.status = !currentReading ? 'stale' :
      snapshot.state === 'Rever' || snapshot.state === 'Atenção' ? 'bad' :
      snapshot.state === 'Estável' && snapshot.coverage >= 99.5 ? 'observed' : 'stale';
    const elapsed = Math.max(0, Math.floor(age / 60000));
    output.textContent = 'Decision Center · ' + snapshot.state +
      ' · cobertura ' + Math.round(snapshot.coverage) + '% · ' +
      (currentReading ? 'leitura atual do dossier' : 'leitura anterior da sessão · confirmar após alterações à carteira') +
      ' · Fonte: motor de decisão da carteira';
  }

  // Read existing published dashboard DOM only. No parallel feeds or financial estimates.
  function syncDailyBrief(host) {
    const update = (key, value) => {
      const node = host.querySelector('[data-vi-brief="'+key+'"]');
      if (node) node.textContent = value;
    };
    const barometer = document.getElementById('vestraMarketSentimentCard');
    const score = barometer?.querySelector('.dms-score')?.textContent?.trim();
    const label = barometer?.querySelector('.dms-label')?.textContent?.trim();
    const number = Number.parseInt(score || '', 10);
    update('market', Number.isInteger(number) && number >= 0 && number <= 100 && label
      ? number+'/100 · '+label+' · Abrir evolução e AAII'
      : 'Sem leitura verificada · abrir barómetro');
    const news = document.getElementById('vestraDailyNewsCard');
    const article = news?.querySelector('.vestra-daily-news-item');
    // Read the headline owner only: badge and metadata must never be glued to it.
    const headline = article?.querySelector('strong')?.textContent?.replace(/\s+/g,' ').trim();
    update('news', headline ? headline.slice(0,145) : 'Notícias ainda não disponíveis · abrir módulo');
    const events = document.getElementById('dashboardWeeklyEventsCard');
    const cards = Array.from(events?.querySelectorAll('.weekly-events-list .weekly-event') || []);
    const today = new Date();
    const todayKey = [today.getFullYear(), String(today.getMonth()+1).padStart(2,'0'), String(today.getDate()).padStart(2,'0')].join('-');
    const upcoming = cards.find(card => (card.dataset.weeklyEventDate || '') >= todayKey);
    const selected = upcoming;
    // The weekly event button has separate day/ticker/name/type nodes.
    // Joining its full textContent loses separators and creates unreadable strings.
    const eventParts = selected ? [
      selected.querySelector('.weekly-event__day')?.textContent?.trim(),
      selected.querySelector('.weekly-event__ticker')?.textContent?.trim(),
      selected.querySelector('.weekly-event__name')?.textContent?.trim(),
      selected.querySelector('.weekly-event__type')?.textContent?.trim()
    ].filter(Boolean) : [];
    update('events', eventParts.length ? eventParts.join(' · ').slice(0,160) : 'Sem próximos eventos confirmados nesta vista · abrir agenda');
  }

  function syncCanonicalCards(host) {
    const set = (key, value) => {
      const node = host.querySelector('[data-vi-canonical-'+key+']');
      if (node) node.textContent = value;
    };
    // Strictly mirror already-rendered sources; never synthesize observations.
    const sentiment = document.getElementById('vestraMarketSentimentCard');
    const scoreText = sentiment?.querySelector('.dms-score')?.textContent?.trim();
    const score = Number.parseInt(scoreText || '', 10);
    const label = sentiment?.querySelector('.dms-label')?.textContent?.trim();
    const hasSentiment = Number.isInteger(score) && score >= 0 && score <= 100 && Boolean(label);
    set('score', hasSentiment ? String(score) : '—');
    set('label', hasSentiment ? label : 'Leitura por confirmar');
    const syncCards = (sourceSelector, listSelector, itemSelector, fallback, limit) => {
      const list = host.querySelector(listSelector);
      const source = document.querySelector(sourceSelector);
      if (!list) return;
      const candidates = Array.from(source?.querySelectorAll(itemSelector) || []).slice(0, limit);
      const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
      const isEarnings = itemSelector.includes('weekly-event');
      const texts = candidates.map(node => {
        if (isEarnings) {
          const day = clean(node.querySelector('.weekly-event__day')?.textContent);
          const ticker = clean(node.querySelector('.weekly-event__ticker')?.textContent);
          const company = clean(node.querySelector('.weekly-event__name')?.textContent)
            .replace(/\s*\(The\)\s*$/i, '').replace(/,\s*Inc\.\s*\(The\)$/i, ', Inc.');
          const eps = clean(node.querySelector('.weekly-event__eps')?.textContent);
          const type = clean(node.querySelector('.weekly-event__type')?.textContent);
          return {lines:[day ? day + ' · ' + ticker : ticker, company, eps || type].filter(Boolean), fallback:ticker, earnings:true};
        }
        // Published news cards own distinct badge, headline and provenance fields.
        // Reading their concatenated textContent joins "MERCADO" to the title.
        const articleTitle = clean(node.querySelector('strong,h2,h3,h4,.vestra-daily-news-title,.news-title')?.textContent);
        const sourceMeta = clean(node.querySelector('small')?.textContent);
        const raw = clean(node.innerText || node.textContent);
        const lines = articleTitle ? [articleTitle, sourceMeta].filter(Boolean) :
          (node.innerText || node.textContent || '').split(/\n+/).map(clean).filter(Boolean).slice(0,4);
        return {lines, fallback:articleTitle || raw.slice(0,190)};
      }).filter(item => item.fallback);
      if (!texts.length) {
        list.replaceChildren();
        const placeholder = document.createElement('p');
        placeholder.textContent = fallback;
        list.append(placeholder);
        return;
      }
      // Cloned text only: no new article links, financial values, images or metadata fabricated.
      list.replaceChildren(...texts.map((item, idx) => {
        const card = document.createElement('div');
        card.className = 'vi-editorial-tile';
        const ordinal = document.createElement('span');
        ordinal.textContent = String(idx + 1).padStart(2,'0');
        ordinal.className = 'vi-editorial-index';
        const body = document.createElement('div');
        body.className = 'vi-editorial-content';
        const title = document.createElement('p');
        title.className = 'vi-editorial-title';
        // Preserve natural line boundaries from the live source rather than
        // concatenating dates, tickers and categories into an unreadable string.
        title.textContent = (item.lines[0] || item.fallback).slice(0,110);
        body.append(title);
        const details = item.earnings ? item.lines.slice(1) : [item.lines.slice(1).join(' · ').trim()];
        for (const [lineIndex, line] of details.entries()) {
          if (!line) continue;
          const detail = document.createElement('small');
          detail.className = 'vi-editorial-detail' + (item.earnings && lineIndex === 1 ? ' vi-editorial-eps' : '');
          detail.textContent = line.slice(0,140);
          body.append(detail);
        }
        card.append(ordinal,body);
        return card;
      }));
    };
    syncCards('#dashboardWeeklyEventsCard', '[data-vi-canonical-event-list]',
      '.weekly-events-list .weekly-event',
      'Sem eventos confirmados nesta sessão · abrir calendário semanal.', 3);
    syncCards('#vestraDailyNewsCard', '[data-vi-canonical-news-list]',
      '.vestra-daily-news-item',
      'Sem notícias confirmadas nesta sessão · abrir o módulo de notícias.', 3);
    try {
      const api = window.VestraDashboardPortfolioConcentration;
      if (!api || typeof api.marketHoldings !== 'function' || typeof api.concentrationSnapshot !== 'function') throw Error('indisponível');
      const concentration = api.concentrationSnapshot(api.marketHoldings());
      if (!Number.isInteger(concentration?.count) || concentration.count < 1 ||
          !Number.isFinite(concentration?.top3) || concentration.top3 < 0 || concentration.top3 > 1) throw Error('incompleto');
      set('risk-title', 'Concentração das três maiores posições');
      set('risk-value', (concentration.top3 * 100).toLocaleString('pt-PT', {maximumFractionDigits:1}) + '%');
      const donut = host.querySelector('.vi-risk-donut');
      if (donut) donut.style.setProperty('--vi-risk-percent', String(concentration.top3 * 100) + '%');
      set('risk', 'Peso combinado das três maiores posições de mercado. Indicador de concentração, não diagnóstico de risco global.');
    } catch (_) {
      set('risk-title', 'Concentração por verificar');
      set('risk-value', '—');
      host.querySelector('.vi-risk-donut')?.style.removeProperty('--vi-risk-percent');
      set('risk', 'Sem cobertura suficiente para calcular concentração. Consultar a análise da carteira.');
    }
  }

  function syncWealthHero(host) {
    const value = host.querySelector('[data-vi-wealth]');
    const assets = host.querySelector('[data-vi-assets]');
    if (!value || !assets) return;
    const changes = host.querySelector('[data-vi-wealth-changes]');
    const nativeChanges = document.getElementById('kpiChanges');
    const nativeText = (nativeChanges?.innerText || nativeChanges?.textContent || '').replace(/\s+/g, ' ').trim();

    const privacy = document.getElementById('btnDashboardPrivacy');
    const concealed = privacy?.getAttribute('aria-pressed') === 'true';
    const viPrivacy = host.querySelector('[data-vi-privacy]');
    if (viPrivacy) {
      viPrivacy.setAttribute('aria-pressed', concealed ? 'true' : 'false');
      viPrivacy.setAttribute('aria-label', concealed ? 'Mostrar valores patrimoniais' : 'Ocultar valores patrimoniais');
      viPrivacy.title = concealed ? 'Mostrar valores' : 'Ocultar valores';
      viPrivacy.textContent = concealed ? '◌' : '◉';
    }
    if (concealed) {
      value.textContent = '••• €';
      assets.textContent = 'Valores ocultos';
      if (changes) changes.textContent = 'Variações ocultas';

      return;
    }
    // The native dashboard is lazy-rendered. Always prefer the canonical
    // portfolio totals instead of reading a possibly stale DOM KPI.
    const totals = window.VestraFinancialTotals?.();
    const money = amount => new Intl.NumberFormat('pt-PT', {
      style: 'currency', currency: 'EUR', maximumFractionDigits: 0
    }).format(amount);
    if (totals && [totals.net, totals.assetsTotal, totals.liabsTotal].every(Number.isFinite)) {
      value.textContent = money(totals.net);
      assets.textContent = 'Ativos ' + money(totals.assetsTotal) + ' | Passivos ' + money(totals.liabsTotal);
    } else {
      value.textContent = '—';
      assets.textContent = 'Património ainda a carregar';
    }
    if (changes) {
      const valid = nativeText && !/a carregar|calculando|indisponível/i.test(nativeText);
      changes.textContent = valid ? nativeText.slice(0, 160) : 'Variações ainda não confirmadas';
    }

  }

  function init() {
    const view = document.getElementById('viewDashboard');
    const host = document.getElementById('vestraIntelligenceHome');
    if (!view || !host) return;
    host.hidden = false;
    view.classList.add('vi-preview-active');
    host.dataset.legacyOpen = 'false';
    const historyDisclosure = document.getElementById('v2-history-disclosure');
    if (historyDisclosure) historyDisclosure.open = false;
    const returnButton = document.getElementById('btnReturnIntelligence');
    if (returnButton) returnButton.addEventListener('click', () => {
      host.dataset.legacyOpen = 'false';
      if (returnButton?.parentElement) returnButton.parentElement.style.removeProperty('display');
      if (typeof window.setView === 'function') window.setView('dashboard');
      host.scrollIntoView({behavior:'smooth', block:'start'});
    });
    syncExistingBarometer(host);
    refreshLivePulse(host);
    showPrebreakoutSpotlight(host);
    syncWealthHero(host);
    syncDailyBrief(host);
    syncCanonicalCards(host);
    syncPortfolioEvidence(host);
    syncDecisionCenter(host);
    window.addEventListener('vestra:dashboard-privacy-changed', () => syncWealthHero(host));
    window.addEventListener('vestra:portfolio-totals-updated', () => {
      syncWealthHero(host);
      syncPortfolioEvidence(host);
      syncDecisionCenter(host);
    });
    window.addEventListener('vestra:market-sheet-changed', () => syncDecisionCenter(host));
    window.addEventListener('vestra:local-state-writing', () => {
      lastDecision = null;
      const output = host.querySelector('[data-vestra-decision-state]');
      if (output) {
        output.dataset.status = 'missing';
        output.textContent = 'Decision Center · carteira ou estado local alterado · reabrir análise para atualizar';
      }
    });
    window.addEventListener('vestra:dashboard-signal-updated', event => {
      if (event?.detail?.source === 'market-sentiment') { syncExistingBarometer(host); syncDailyBrief(host); syncCanonicalCards(host); }
    });
    window.addEventListener('vestra:weekly-data-refreshed', () => { syncDailyBrief(host); syncCanonicalCards(host); });
    window.addEventListener('focus', () => { refreshLivePulse(host); syncDailyBrief(host); syncWealthHero(host); syncCanonicalCards(host); });
    // The underlying modules hydrate asynchronously; retry a bounded number of times.
    [1200, 3500, 6500].forEach(delay => setTimeout(() => { syncDailyBrief(host); syncWealthHero(host); }, delay));
    showCoverage(host);
    showProspectiveValidation(host);
    host.dataset.vestraIntelligence = '1';
    host.setAttribute('data-theme', document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
    host.addEventListener('click', event => {
      if (event.target.closest('button[data-vi-privacy]')) {
        document.getElementById('btnDashboardPrivacy')?.click();
        syncWealthHero(host);
        return;
      }
      const sectionButton = event.target.closest('button[data-vestra-dashboard-section], button[data-vi-canonical-section]');
      if (sectionButton && host.contains(sectionButton)) {
        const targetId = sectionButton.dataset.vestraDashboardSection || sectionButton.dataset.viCanonicalSection;
        if (!['vestraMarketSentimentCard', 'vestraDailyNewsCard', 'dashboardWeeklyEventsCard'].includes(targetId)) return;
        // Reveal the original, fully functional dashboard before navigating into it.
        if (typeof window.setView === 'function') window.setView('dashboard');
        host.dataset.legacyOpen = 'true';
        if (returnButton?.parentElement) returnButton.parentElement.style.setProperty('display','block','important');
        const scrollToSection = () => {
          const destination = document.getElementById(targetId);
          if (destination) destination.scrollIntoView({behavior:'smooth',block:'start'});
        };
        requestAnimationFrame(() => requestAnimationFrame(scrollToSection));
        return;
      }
      const button = event.target.closest('button[data-vestra-go]');
      if (!button || !host.contains(button)) return;
      const target = button.dataset.vestraGo;
      if (!['market', 'portfolio', 'dashboard'].includes(target)) return;
      if (target === 'dashboard') {
        if (typeof window.setView === 'function') window.setView('dashboard');
        host.dataset.legacyOpen = 'true';
        if (returnButton?.parentElement) returnButton.parentElement.style.setProperty('display','block','important');
        const legacy = document.querySelector('#viewDashboard .v2-detail-chapter-nav') || document.querySelector('#viewDashboard .vi-back-to-intelligence') || document.querySelector('#viewDashboard .v2-home-stage');
        if (legacy && typeof legacy.scrollIntoView === 'function') legacy.scrollIntoView({behavior:'smooth', block:'start'});
        return;
      }
      if (target === 'market' && button.dataset.vestraTicker) {
        const ticker = button.dataset.vestraTicker;
        if (!/^[A-Z0-9.\\-]{1,16}$/.test(ticker)) return;
        if (button.disabled) return;
        button.disabled = true;
        // Open the exact published ticker's canonical dossier, not the generic Market tab.
        Promise.resolve().then(async () => {
          const market = window.VestraMarket;
          if (typeof market?.ensureLoaded === 'function') await market.ensureLoaded();
          await window.VestraNavigation?.openCompany?.(ticker,{origin:'market',sourceNode:button});
          if (document.getElementById('marketSheet')?.dataset.ticker === ticker) return;
          // If the published ticker has no dossier in the current universe,
          // keep the user's research intent by offering the prefilled Market search.
          const search = document.getElementById('marketSearch');
          if (search) {
            search.value = ticker;
            search.dispatchEvent(new Event('input',{bubbles:true}));
            search.focus();
          }
        }).catch(() => {
          const search = document.getElementById('marketSearch');
          if (search) {
            search.value = ticker;
            search.dispatchEvent(new Event('input',{bubbles:true}));
            search.focus();
          }
        }).finally(() => { button.disabled = false; });
        return;
      }
      if (typeof window.setView === 'function') window.setView(target === 'portfolio' ? 'assets' : target);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
