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

  // Present only observed, attributable priorities. Unverified research remains
  // available as navigation, never masquerading as a decision.
  function syncVerifiedPriorities(host) {
    const area = host.querySelector('.vi-investigation-disclosure');
    if (!area) return;
    const cards = [...area.querySelectorAll('.vi-decisions > .vi-action')];
    if (cards.length !== 3) return;
    const concentration = host.querySelector('[data-vestra-portfolio-evidence]');
    const decision = host.querySelector('[data-vestra-decision-state]');
    const concentrationObserved = concentration?.dataset.status === 'observed';
    const decisionAlert = decision?.dataset.status === 'bad';
    // A count of measured positions is not itself a concentration warning.
    // Keep neutral portfolio navigation reachable without requiring evidence.
    cards[0].hidden = false;
    const concentrationTitle = cards[0].querySelector('strong');
    if (concentrationTitle) concentrationTitle.textContent = concentrationObserved
      ? 'Distribuição da carteira · dado observado'
      : 'Consultar distribuição da carteira';
    // No canonical identified asymmetric opportunity is supplied here.
    // Market exploration is navigation, not an inferred investment signal.
    cards[1].hidden = false;
    // The Decision Center's current alert is the only defensible thesis action.
    cards[2].hidden = !decisionAlert;
    const count = Number(concentrationObserved) + Number(decisionAlert);
    const summary = area.querySelector('summary');
    if (summary) summary.textContent = decisionAlert
      ? 'Atenção na carteira · decisão verificada'
      : concentrationObserved
        ? 'Carteira medida · explorar informação disponível'
        : 'Sem alertas confirmados · explorar Carteira e Mercado';
    // Order the only verified warning first; exploration never outranks it.
    // Restore the stable default order when the warning is absent or stale.
    const container = cards[0].parentElement;
    if (container) {
      container.append(cards[0], cards[1], cards[2]);
      if (decisionAlert) container.prepend(cards[2]);
      [...container.querySelectorAll('.vi-action')].forEach((card, index) => {
        const number = card.querySelector('.vi-number');
        if (number) number.textContent = String(index + 1).padStart(2, '0');
      });
    }
    const heading = host.querySelector('.vi-priorities .vi-heading p');
    if (heading) heading.textContent = decisionAlert
      ? 'Uma situação da carteira merece revisão. Verifica a cobertura e o diagnóstico antes de agir.'
      : 'Sem alertas confirmados. Explora a carteira e o mercado sem assumir recomendações.';
    // Do not conceal primary navigation when evidence is unavailable.
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
      // A measured top-three share is information, not evidence of a risk breach.
      // Never infer a concentration alert from the mere existence of positions.
      const share = (snapshot.top3 * 100).toLocaleString('pt-PT', {
        minimumFractionDigits: 1, maximumFractionDigits: 1
      });
      output.textContent = '3 maiores posições: ' + share + '% de ' +
        snapshot.count + ' posições de mercado observadas · Fonte: motor de concentração da carteira · análise, não alerta';
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

  async function showPrebreakoutVisuals(panel, pick) {
    if (!pick?.ticker || !panel.isConnected) return;
    const container = document.createElement('div');
    container.className = 'vi-pb-visuals';
    const price = document.createElement('section');
    const profile = document.createElement('section');
    price.className = 'vi-pb-visual';
    profile.className = 'vi-pb-visual';
    const caption = (parent, value) => {
      const node = document.createElement('p');
      node.className = 'vi-pb-visual-label';
      node.textContent = value;
      parent.append(node);
    };
    caption(price, 'PREÇO · HISTÓRICO REAL');
    caption(profile, 'PERFIL VESTRA · 5 EIXOS');
    const placeholder = (parent, value) => {
      const node = document.createElement('p');
      node.className = 'vi-pb-visual-empty';
      node.textContent = value;
      parent.append(node);
    };
    placeholder(price, 'Histórico por confirmar');
    placeholder(profile, 'Fundamentais por confirmar');
    container.append(price, profile);
    const foot = panel.querySelector('.vi-pb-foot');
    if (foot) foot.before(container); else panel.append(container);
    // The Market core is lazy: the Home must resolve published dossier shards
    // without forcing market.js (or the quote refresh engine) to start.
    const loader = window.VestraMarketData?.hydrateTicker;
    let stock=null;
    try {
      if (typeof loader === 'function') stock=await loader(pick.ticker);
      if (!stock) {
        const manifestResponse=await fetch('./data/dossiers-manifest.json',{cache:'no-store'});
        if (!manifestResponse.ok) return;
        const manifest=await manifestResponse.json();
        const bucket=manifest?.tickers?.[pick.ticker];
        if (typeof bucket!=='string' || !/^[A-Z0-9]{2}$/.test(bucket)) return;
        const dossierResponse=await fetch('./data/dossiers/'+bucket+'.json',{cache:'no-store'});
        if (!dossierResponse.ok) return;
        stock=(await dossierResponse.json())?.stocks?.[pick.ticker];
        if (stock?.ticker!==pick.ticker) return;
      }
    } catch (_) { return; }
    if (!panel.isConnected || panel.querySelector('.vi-pb-ticker')?.textContent !== pick.ticker || !stock) return;
    const makeSvg = (width, height, label) => {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 '+width+' '+height);
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', label);
      return svg;
    };
    const shape = (svg, type, attrs) => {
      const node = document.createElementNS('http://www.w3.org/2000/svg', type);
      Object.entries(attrs).forEach(([key,value]) => node.setAttribute(key, String(value)));
      svg.append(node);
      return node;
    };
    const history = Array.isArray(stock.price_history_1y) ? stock.price_history_1y : [];
    const close = history.map(row => Number(typeof row === 'number' ? row : row?.close ?? row?.price))
      .filter(value => Number.isFinite(value) && value > 0).slice(-120);
    if (close.length >= 2) {
      const low = Math.min(...close), high = Math.max(...close), spread = high-low || 1;
      const points = close.map((value, i) =>
        (6+i*208/(close.length-1)).toFixed(1)+','+(65-(value-low)*51/spread).toFixed(1)).join(' ');
      const svg = makeSvg(220, 76, 'Cotação histórica real de '+pick.ticker+' · '+close.length+' observações');
      shape(svg, 'polyline', {points, fill:'none', stroke:'currentColor', 'stroke-width':2.5,
        'stroke-linecap':'round', 'stroke-linejoin':'round', 'vector-effect':'non-scaling-stroke'});
      price.replaceChildren();
      caption(price, 'PREÇO · ÚLTIMAS '+close.length+' OBSERVAÇÕES');
      price.append(svg);
    }
    const numeric = v => v === null || v === undefined || v === '' ? null :
      (Number.isFinite(Number(v)) ? Math.max(0,Math.min(100,Number(v))) : null);
    const blend = groups => {
      let sum=0, total=0, observed=false;
      for (const [raw,weight] of groups) {
        const v=numeric(raw);
        sum+=(v===null?50:v)*weight;
        total+=weight;
        if(v!==null) observed=true;
      }
      return observed && total>0 ? sum/total : null;
    };
    // Same component fields and weights as market.js dossierRadarAxes.
    const axes = [
      numeric(stock.value_pct),
      blend([[stock.growth_pct,.65],[stock.estimate_momentum_score,.35]]),
      blend([[stock.quality_pct,.45],[stock.stability_pct,.30],[stock.execution_pct,.25]]),
      blend([[stock.balance_pct,.40],[stock.cashflow_pct,.35],[stock.earnings_quality_pct,.25]]),
      null
    ];
    // Mirror the existing dossier's dividend axis; non-payers remain N/A.
    const actual = value => value === null || value === undefined || value === '' ||
      !Number.isFinite(Number(value)) ? null : Number(value);
    const asPct = value => value === null ? null : (Math.abs(value)<=1 ? value*100 : value);
    const yieldPct=asPct(actual(stock.dividend_yield));
    if (yieldPct !== null && yieldPct>0) {
      const median=asPct(actual(stock.sector_dividend_yield_median));
      const yieldScore=median !== null && median>0 ? Math.max(0,Math.min(100,50*yieldPct/median)) :
        Math.max(0,Math.min(100,yieldPct/4*100));
      const payout=asPct(actual(stock.payout_ratio));
      const payoutScore=payout===null?null:payout<=0?50:payout<25?60+payout/25*20:
        payout<=70?90:payout<=100?90-(payout-70)/30*60:Math.max(0,30-(payout-100));
      const coverage=actual(stock.dividend_fcf_coverage);
      const coverageScore=coverage===null?null:coverage>=2?100:coverage>=1?60+(coverage-1)*40:
        coverage>=0?20+coverage*40:0;
      axes[4]=blend([[yieldScore,.35],[payoutScore,.30],[coverageScore,.35]]);
    }
    if (axes.slice(0,4).some(x=>x!==null)) {
      const svg=makeSvg(180,180,'Perfil fundamental compacto de '+pick.ticker+
        ' · Valor, Futuro, Histórico, Saúde e Dividendo (N/A quando não aplicável)');
      const point=(idx,score,rad=66) => {
        const angle=(-90+idx*72)*Math.PI/180;
        return [90+Math.cos(angle)*rad*score/100,90+Math.sin(angle)*rad*score/100];
      };
      for(const level of [25,50,75,100]){
        shape(svg,'polygon',{points:axes.map((_,i)=>point(i,level).map(v=>v.toFixed(1)).join(',')).join(' '),
          fill:'none',stroke:'currentColor','stroke-opacity':'.19','stroke-width':'1'});
      }
      const polygon=axes.map((v,i)=>point(i,v===null?50:v).map(x=>x.toFixed(1)).join(',')).join(' ');
      shape(svg,'polygon',{points:polygon,fill:'currentColor','fill-opacity':'.12',
        stroke:'currentColor','stroke-width':'2.5'});
      axes.forEach((v,i)=>{if(v!==null){const [cx,cy]=point(i,v);
        shape(svg,'circle',{cx,cy,r:2.5,fill:'currentColor'});}});
      profile.replaceChildren();
      caption(profile,'PERFIL FUNDAMENTAL · 5 EIXOS');
      profile.append(svg);
      const labels=document.createElement('p');
      labels.className='vi-pb-visual-axes';
      labels.textContent=['Valor','Futuro','Histórico','Saúde','Dividendo'].map((label,i)=>
        label+' '+(axes[i]===null?'N/A':Math.round(axes[i]))).join(' · ');
      profile.append(labels);
    }
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
    // The research link mirrors the scanner's canonical focus; it never
    // independently promotes a high-scoring watchlist entry to a candidate.
    const updateResearchFocus = (pick, stamp) => {
      const card = host.querySelector('.vi-priorities .vi-action[data-vestra-go="market"]');
      if (!card) return;
      const title = card.querySelector('strong');
      const detail = card.querySelector('small');
      if (!title || !detail) return;
      if (!pick) {
        title.textContent = 'Explorar investigação no Mercado';
        detail.textContent = 'Sem candidato canónico válido nesta leitura. Consultar o scanner sem inferir recomendação.';
        card.removeAttribute('data-vestra-ticker');
        return;
      }
      title.textContent = pick.ticker + ' · investigar pré-breakout';
      detail.textContent = 'Distância à resistência ' + pick.distancePct.toFixed(2).replace('.', ',') +
        '% · Score técnico ' + Math.round(pick.score) +
        '/100 · OHLCV ' + pick.date + ' · leitura publicada ' +
        new Date(stamp).toLocaleDateString('pt-PT') +
        ' · não é breakout confirmado nem recomendação.';
      // Keep the established Market navigation; detailed ticker navigation
      // remains the responsibility of the scanner spotlight button.
      card.removeAttribute('data-vestra-ticker');
    };
    updateResearchFocus(null, null);
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
      const hasCanonicalFocus = Object.prototype.hasOwnProperty.call(feed, 'daily_focus');
      const canonicalPick = hasCanonicalFocus && focus && typeof focus === 'object' && focus.status === 'research_candidate'
        ? qualified.find(row => row.ticker === focus.ticker &&
            row.date === focus.signal_date &&
            row.distancePct <= 4 && row.vcpConfirmed === true &&
            row.source === 'yahoo:daily_ohlcv') : null;
      const pick = hasCanonicalFocus ? canonicalPick : qualified[0];
      updateResearchFocus(hasCanonicalFocus ? canonicalPick : null, stamp);
      if (pick) {
        render(pick.ticker+' · Próximo do pivot',
          'Score técnico '+Math.round(pick.score)+'/100 · '+pick.distancePct.toFixed(2).replace('.',',')+
          '% abaixo da resistência · volume a secar comprovado. Investigar tese, risco e liquidez antes de qualquer decisão.',
          source+' · Sinal '+pick.date+' · VCP '+(pick.vcpConfirmed === true ? 'confirmada' : 'não confirmada')+' · Volume a secar '+(pick.volumeDry === true ? 'confirmado' : 'não confirmado')+' · Melhor sinal da amostra, não do mercado inteiro · Risco: breakout ainda não confirmado.', true, pick, true);
        void showPrebreakoutVisuals(panel, pick);
      } else if (hasCanonicalFocus) {
        render('Sem candidato canónico validado',
          'O radar não publicou um sinal principal verificável. Não é correto promover outra ação no Dashboard.',
          source+' · Sem substituição independente do sinal canónico.', true);
      } else if (rows.length) {
        const watch = rows.sort((a,b)=>b.score-a.score || a.ticker.localeCompare(b.ticker))[0];
        render('Sem pré-breakout qualificado hoje',
          'Base em compressão. Ainda sem confirmação completa; não é uma oportunidade antecipatória validada.',
          source+' · Vigilância, não recomendação.',true,watch,false);
        // A compression watch still has a real company dossier: present its
        // observed price and fundamental context without promoting its stage.
        void showPrebreakoutVisuals(panel, watch);
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

  // Independent, bounded news hydration. The old Dashboard DOM is optional.
  async function loadPublishedNews(host) {
    const list = host.querySelector('[data-vi-canonical-news-list]');
    if (!list || list.dataset.publishedFeed === 'true') return;
    try {
      const response = await fetch('./data/dashboard-news.json', {cache:'no-store'});
      if (!response.ok) return;
      const feed = await response.json();
      const generated = Date.parse(feed?.generated_at);
      if (!Number.isFinite(generated) || generated > Date.now() + 3600000 ||
          Date.now() - generated > 72 * 3600000 || !Array.isArray(feed.items)) return;
      const articles = feed.items.filter(item => {
        const published = Date.parse(item?.published);
        return typeof item?.title === 'string' && item.title.trim().length >= 15 &&
          typeof item?.source === 'string' && item.source.trim().length > 0 &&
          typeof item?.link === 'string' && /^https:\/\//.test(item.link) &&
          Number.isFinite(published) && published <= Date.now() + 3600000 &&
          Date.now() - published <= 72 * 3600000;
      }).sort((a,b) => (Number(b.impact_score) || 0) - (Number(a.impact_score) || 0) ||
        Date.parse(b.published) - Date.parse(a.published)).slice(0,3);
      if (!articles.length) return;
      const fragment = document.createDocumentFragment();
      articles.forEach((item,index) => {
        const tile = document.createElement('div');
        tile.className = 'vi-editorial-tile';
        const ordinal = document.createElement('span');
        ordinal.className = 'vi-editorial-index';
        ordinal.textContent = String(index+1).padStart(2,'0');
        const content = document.createElement('div');
        content.className = 'vi-editorial-content';
        const headline = document.createElement('p');
        headline.className = 'vi-editorial-title';
        headline.textContent = item.title.slice(0,130);
        const meta = document.createElement('small');
        meta.className = 'vi-editorial-detail';
        meta.textContent = item.source + ' · ' + new Date(item.published).toLocaleDateString('pt-PT');
        content.append(headline,meta); tile.append(ordinal,content); fragment.append(tile);
      });
      // Prefer the canonical rendered news cards once they exist; otherwise
      // display the real published feed, never an empty-session assertion.
      const native = document.querySelector('#vestraDailyNewsCard .vestra-daily-news-item');
      if (!native) { list.replaceChildren(fragment); list.dataset.publishedFeed='true'; }
    } catch (_) { /* No false no-news claim when offline. */ }
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
        if (list.dataset.publishedFeed === 'true') return;
        list.replaceChildren();
        const placeholder = document.createElement('p');
        // Keep the honest no-data state in the same compact editorial type scale.
        placeholder.className = 'vi-editorial-title';
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
      'Sem calendário futuro verificado · consultar a agenda semanal.', 3);
    syncCards('#vestraDailyNewsCard', '[data-vi-canonical-news-list]',
      '.vestra-daily-news-item',
      'A consultar notícias publicadas e fontes verificáveis…', 3);
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
    const income = host.querySelector('[data-vi-income-monthly]');
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
      if (income) income.textContent = '••• €';

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
    if (income) {
      // Mirror the already calculated dashboard KPI, never infer income from
      // capital, yield or dividend forecasts when no verified KPI is available.
      const nativeIncome = document.getElementById('kpiPassiveMonthly');
      const monthly = (nativeIncome?.textContent || '').replace(/\\s+/g, ' ').trim();
      income.textContent = monthly && /\\d/.test(monthly) &&
        !/a carregar|calculando|indisponível/i.test(monthly) ? monthly.slice(0,48) : 'Por confirmar';
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
    void loadPublishedNews(host);
    syncPortfolioEvidence(host);
    syncDecisionCenter(host);
    syncVerifiedPriorities(host);
    window.addEventListener('vestra:dashboard-privacy-changed', () => syncWealthHero(host));
    window.addEventListener('vestra:portfolio-totals-updated', () => {
      syncWealthHero(host);
      syncPortfolioEvidence(host);
      syncDecisionCenter(host);
      syncVerifiedPriorities(host);
    });
    window.addEventListener('vestra:market-sheet-changed', () => { syncDecisionCenter(host); syncVerifiedPriorities(host); });
    window.addEventListener('vestra:local-state-writing', () => {
      lastDecision = null;
      const output = host.querySelector('[data-vestra-decision-state]');
      if (output) {
        output.dataset.status = 'missing';
        output.textContent = 'Decision Center · carteira ou estado local alterado · reabrir análise para atualizar';
      }
      syncVerifiedPriorities(host);
    });
    window.addEventListener('vestra:dashboard-signal-updated', event => {
      if (event?.detail?.source === 'market-sentiment') { syncExistingBarometer(host); syncDailyBrief(host); syncCanonicalCards(host); }
    });
    window.addEventListener('vestra:weekly-data-refreshed', () => { syncDailyBrief(host); syncCanonicalCards(host); });
    window.addEventListener('focus', () => { refreshLivePulse(host); syncDailyBrief(host); syncWealthHero(host); syncCanonicalCards(host); void loadPublishedNews(host); });
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
