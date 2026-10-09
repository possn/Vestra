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
    const headline = article?.textContent?.replace(/\\s+/g,' ').trim();
    update('news', headline ? headline.slice(0,100) : 'Notícias ainda não disponíveis · abrir módulo');
    const events = document.getElementById('dashboardWeeklyEventsCard');
    const event = events?.querySelector('.weekly-events-list .weekly-event');
    const eventLabel = event?.textContent?.replace(/\\s+/g,' ').trim();
    update('events', eventLabel ? eventLabel.slice(0,100) : 'Consultar calendário e eventos da semana');
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
    set('market', hasSentiment
      ? 'Barómetro de mercado baseado em sinais de preço; não equivale ao inquérito AAII. Abrir para evolução e metodologia.'
      : 'Sem barómetro observado nesta sessão. Abrir o módulo para fontes, AAII e metodologia.');
    const syncCards = (sourceSelector, listSelector, itemSelector, fallback, limit) => {
      const list = host.querySelector(listSelector);
      const source = document.querySelector(sourceSelector);
      if (!list) return;
      const candidates = Array.from(source?.querySelectorAll(itemSelector) || []).slice(0, limit);
      const texts = candidates.map(node => ({
        lines: (node.innerText || node.textContent || '').split(/\n+/)
          .map(part => part.replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0,4),
        fallback: (node.textContent || '').replace(/\s+/g, ' ').trim().slice(0,190)
      })).filter(item => item.fallback);
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
        const remainder = item.lines.slice(1).join(' · ').trim();
        if (remainder) {
          const detail = document.createElement('small');
          detail.className = 'vi-editorial-detail';
          detail.textContent = remainder.slice(0,140);
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
    const concealed = privacy?.getAttribute('aria-pressed') === 'true' ||
      /mostrar valores/i.test(document.getElementById('dashboardPrivacyLabel')?.textContent || '');
    if (concealed) {
      value.textContent = '••• €';
      assets.textContent = 'Valores ocultos';
      if (changes) changes.textContent = 'Variações ocultas';

      return;
    }
    const originalValue = document.getElementById('kpiNet')?.textContent?.trim();
    const originalAssets = document.getElementById('kpiAP')?.textContent?.trim();
    value.textContent = originalValue && originalValue !== '0 €' ? originalValue : '—';
    assets.textContent = originalAssets && !/Ativos 0 € \\| Passivos 0 €/.test(originalAssets) ?
      originalAssets : 'Património ainda a carregar';
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
    const returnButton = document.getElementById('btnReturnIntelligence');
    if (returnButton) returnButton.addEventListener('click', () => {
      host.dataset.legacyOpen = 'false';
      if (returnButton?.parentElement) returnButton.parentElement.style.removeProperty('display');
      if (typeof window.setView === 'function') window.setView('dashboard');
      host.scrollIntoView({behavior:'smooth', block:'start'});
    });
    syncExistingBarometer(host);
    syncWealthHero(host);
    syncDailyBrief(host);
    syncCanonicalCards(host);
    syncPortfolioEvidence(host);
    syncDecisionCenter(host);
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
    window.addEventListener('focus', () => { syncDailyBrief(host); syncWealthHero(host); syncCanonicalCards(host); });
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
        const legacy = document.querySelector('#viewDashboard .vi-back-to-intelligence') || document.querySelector('#viewDashboard .v2-home-stage');
        if (legacy && typeof legacy.scrollIntoView === 'function') legacy.scrollIntoView({behavior:'smooth', block:'start'});
        return;
      }
      if (typeof window.setView === 'function') window.setView(target === 'portfolio' ? 'assets' : target);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
