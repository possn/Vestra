const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard renders weekly macro catalysts plus portfolio earnings', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  // Isolate this deterministic fixture from production historical earnings.
  await page.route('**/data/earnings-events.json', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ schema: 'vestra_earnings_events_v1', events: [] }),
  }));
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  // Let startup sources settle before the deterministic fixture, so a late
  // archive/startup render does not replace this test's selected week.
  await page.waitForLoadState('networkidle', { timeout: 25000 });

  // Reproduce the real default Dashboard state: secondary cards are collapsed.
  await page.evaluate(() => document.getElementById('viewDashboard')?.classList.remove('dash-secondary-open'));

  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 7, 9, 0, 0),
      portfolioTickers: new Set(['NVDA']),
      stocks: [
        { ticker:'NVDA', name:'NVIDIA Corporation', quote_type:'EQUITY', market_cap:4_000_000_000_000, analyst_next_earnings_date:'2026-09-08' },
        { ticker:'AAPL', name:'Apple Inc.', quote_type:'EQUITY', market_cap:3_500_000_000_000, analyst_next_earnings_date:'2026-09-09' },
        { ticker:'ETF1', name:'Not an earnings issuer', quote_type:'ETF', market_cap:8_000_000_000, analyst_next_earnings_date:'2026-09-07' },
      ],
      macroEvents: {
        events: [
          { date:'2026-09-10', short_title:'PPI EUA', title:'PPI EUA · agosto', category:'inflation', region:'EUA', importance:'high', source:'bls', time_local:'08:30 ET' },
          { date:'2026-09-11', short_title:'CPI EUA', title:'CPI EUA · agosto', category:'inflation', region:'EUA', importance:'critical', source:'bls', time_local:'08:30 ET' },
          { date:'2026-09-15', short_title:'FOMC', title:'FOMC', category:'central_bank', region:'EUA', importance:'critical', source:'fed' },
        ]
      }
    });
  });

  const card = page.locator('#dashboardWeeklyEventsCard');
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card.locator('.weekly-events-title')).toHaveText('Eventos da semana');
  await expect(card.locator('.weekly-events-range')).toHaveText('7/09 – 13/09');

  // Weekly cards now use an index because the first tap opens the event detail;
  // ticker identity is carried by the dossier action inside an earnings detail.
  const events = card.locator('[data-weekly-event-index]');
  await expect(events).toHaveCount(3);
  // The imminent critical CPI must be visible without expanding the rail;
  // earnings remain available in the same preview and full agenda.
  await expect(events.nth(0)).toContainText('CPI EUA');
  await expect(events.nth(0)).toContainText('Impacto elevado');
  await expect(events.nth(1)).toContainText('NVDA');
  await expect(events.nth(1)).toContainText('NVIDIA Corporation');
  await expect(events.nth(1)).toContainText('No portefólio');
  await expect(events.nth(2)).toContainText('AAPL');
  await expect(events.nth(2)).toContainText('Apple Inc.');
  await card.locator('[data-weekly-events-toggle]').click();
  expect(await events.count()).toBeGreaterThanOrEqual(4);
  await expect(events.filter({ hasText: 'CPI EUA' })).toHaveCount(1);
  await expect(events.filter({ hasText: 'PPI EUA' })).toHaveCount(1);
  await expect(card).toContainText('Inflação');
  await expect(card).toContainText('Impacto elevado');
  await expect(card).not.toContainText('FOMC');
  await expect(card).not.toContainText('ETF1');

  await events.nth(1).click();
  const detail = page.locator('#dashboardWeeklyEventDetail');
  await expect(detail).toBeVisible();
  await expect(detail).toContainText('NVIDIA Corporation');
  await expect(detail.locator('[data-weekly-detail-ticker="NVDA"]')).toBeVisible();

  const order = await page.locator('#viewDashboard > .card').evaluateAll(nodes => nodes.map(node => node.id || node.className));
  const heroIndex = order.findIndex(value => String(value).includes('hero'));
  const weeklyIndex = order.findIndex(value => value === 'dashboardWeeklyEventsCard');
  expect(weeklyIndex).toBe(heroIndex + 1);
  await expect(page.locator('#viewDashboard .card.hero')).toBeVisible();
  await expect(card).toBeVisible();
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: CPI structured BLS metrics render as published results instead of pending', async ({ page }) => {
  // This test validates macro-event evidence, not the market-wide stock index.
  // A minimal valid packed universe prevents the unrelated 2 MB startup data
  // from blocking WebKit's layout/visibility checks on a slow runner.
  await page.route('**/data/stocks-startup.json', route => route.fulfill({
    status:200,contentType:'application/json',
    body:JSON.stringify({layout:'field_rows_v1',fields:['ticker','name','quote_type'],rows:[['TEST','Fixture Company','EQUITY']]})
  }));
  // The CPI fixture is self-contained: avoid large unrelated earnings downloads
  // saturating WebKit while the sheet's official metrics are inspected.
  await page.route('**/data/earnings-latest.json', route => route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify({schema:'vestra_earnings_latest_v1',stocks:[]}) }));
  await page.route('**/data/earnings-events.json', route => route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify({schema:'vestra_earnings_events_v1',events:[]}) }));
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.context().route('https://www.bls.gov/news.release/cpi.nr0.htm', async route => {
    await route.fulfill({ status: 200, contentType: 'text/html', body: '<title>BLS CPI</title><p>official</p>' });
  });
  await page.route('**/data/macro-events.json', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 2,
        generated_at: '2026-09-18T07:00:00Z',
        source_status: { bls:{state:'fresh'}, fed:{state:'fresh'}, bea:{state:'fresh'}, ecb:{state:'fresh'}, census:{state:'fresh'} },
        events: [{
          date:'2026-09-18',
          short_title:'CPI EUA',
          title:'CPI EUA',
          category:'inflation',
          region:'EUA',
          importance:'high',
          source:'bls',
          time_local:'7:30 AM CT',
          result_status:'official_release_summary',
          result_summary:'BLS Public Data API · headline +0.4% MoM / +3.4% YoY; core +0.3% MoM / +2.4% YoY.',
          result_released_at:'2026-09-18',
          result_metric_schema:'bls_cpi_v1',
          result_metrics:{ headline_mom_pct:0.4, headline_yoy_pct:3.4, core_mom_pct:0.3, core_yoy_pct:2.4 },
          result_transport:'bls_public_api',
          source_url:'https://www.bls.gov/news.release/cpi.nr0.htm',
        }]
      }),
    });
  });

  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  // Wait for the actual calendar companions rather than global network idle:
  // background market requests need not settle for this deterministic CPI fixture.
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEventsNavigation));
  // The first Dashboard hydration may still be running despite its companion
  // being registered. Await the same source promises before opening the sheet.
  await page.evaluate(async () => {
    await Promise.allSettled([
      window.VestraWeeklyEvents.loadMacroEvents(),
      window.VestraWeeklyEvents.loadLatestEarnings(),
      window.VestraWeeklyEvents.loadEarningsArchive(),
    ]);
  });

  await page.evaluate(() => {
    const events = window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 18, 14, 0, 0),
      portfolioTickers: new Set(),
      stocks: [],
      macroEvents: {
        events: [{
          date:'2026-09-18',
          short_title:'CPI EUA',
          title:'CPI EUA',
          category:'inflation',
          region:'EUA',
          importance:'high',
          source:'bls',
          time_local:'7:30 AM CT',
          result_status:'official_release_summary',
          result_summary:'BLS Public Data API · August 2026: headline +0.4% MoM / +3.4% YoY; core +0.3% MoM / +2.4% YoY.',
          result_released_at:'2026-09-18',
          result_metric_schema:'bls_cpi_v1',
          result_metrics:{ headline_mom_pct:0.4, headline_yoy_pct:3.4, core_mom_pct:0.3, core_yoy_pct:2.4 },
          result_transport:'bls_public_api',
          source_url:'https://www.bls.gov/news.release/cpi.nr0.htm',
        }]
      }
    });
    const cpi = events.find(item => item.kind === 'macro' && item.shortTitle === 'CPI EUA');
    if (!cpi) throw new Error('CPI test fixture missing from selected week');
    window.VestraWeeklyEvents.openDetail(cpi);
    const modal = document.getElementById('dashboardWeeklyEventDetail');
    if (!modal) throw new Error('CPI detail not mounted immediately after openDetail');
    const style = window.getComputedStyle(modal);
    if (style.display === 'none' || style.visibility === 'hidden') throw new Error('CPI detail mounted but hidden: ' + style.display + '/' + style.visibility);
  });

  const detail = page.locator('#dashboardWeeklyEventDetail');
  await expect(detail).toBeVisible();
  await expect(detail).toContainText('Headline MoM');
  await expect(detail).toContainText('+0,4%');
  await expect(detail).toContainText('Headline YoY');
  await expect(detail).toContainText('+3,4%');
  await expect(detail).toContainText('Core MoM');
  await expect(detail).toContainText('+0,3%');
  await expect(detail).toContainText('Core YoY');
  await expect(detail).toContainText('+2,4%');
  await expect(detail).not.toContainText('Resultado ainda não publicado');

  const official = detail.locator('a.weekly-detail-action');
  await expect(official).toHaveAttribute('href', 'https://www.bls.gov/news.release/cpi.nr0.htm');
  const popupPromise = page.waitForEvent('popup');
  await official.tap();
  const popup = await popupPromise;
  await popup.waitForLoadState('domcontentloaded');
  await popup.close();

  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'));
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: false }));
  });
  await expect(detail).toBeVisible();
  await expect(page.locator('#appLoadingOverlay')).toBeHidden();

  const savedReturn = JSON.parse(await page.evaluate(() => localStorage.getItem('vestra:external-return-v1')));
  expect(savedReturn.kind).toBe('weekly-official');
  expect(savedReturn.detailId).toContain('bls:2026-09-18:CPI EUA');

  // Reproduce a real iOS cold-resume after Safari has discarded the PWA.
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  const restoredDetail = page.locator('#dashboardWeeklyEventDetail');
  await expect(restoredDetail).toBeVisible({ timeout: 10_000 });
  await expect(restoredDetail).toContainText('CPI EUA');
  await expect(page.locator('#appLoadingOverlay')).toHaveAttribute('data-news-return-skip', '1');
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 1_500 });
  expect(await page.evaluate(() => localStorage.getItem('vestra:external-return-v1'))).toBeNull();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: reported company earnings replace a stale pending event on the same date', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  // Isolate this deterministic fixture from production historical earnings.
  await page.route('**/data/earnings-events.json', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ schema: 'vestra_earnings_events_v1', events: [] }),
  }));
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  // Let startup sources settle before the deterministic fixture, so a late
  // archive/startup render does not replace this test's selected week.
  await page.waitForLoadState('networkidle', { timeout: 25000 });

  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 10, 22, 0, 0),
      portfolioTickers: new Set(),
      macroEvents: { events: [] },
      stocks: [{
        ticker:'ADBE',
        name:'Adobe Inc.',
        quote_type:'EQUITY',
        market_cap:150_000_000_000,
        analyst_next_earnings_date:'2026-09-10',
        analyst_eps_next_q:4.86,
        analyst_latest_earnings_date:'2026-09-10',
        analyst_latest_eps_estimate:4.86,
        analyst_latest_eps_actual:5.31,
        analyst_latest_eps_surprise_pct:0.0926,
      }],
    });
  });

  const events = page.locator('#dashboardWeeklyEventsCard [data-weekly-event-index]');
  await expect(events).toHaveCount(1);
  await expect(events.first()).toContainText('ADBE');
  await events.first().click();

  const detail = page.locator('#dashboardWeeklyEventDetail');
  await expect(detail).toBeVisible();
  await expect(detail).toContainText('Resultados publicados');
  await expect(detail).toContainText('5,31');
  await expect(detail).toContainText('4,86');
  await expect(detail).toContainText('9,3%');
  await expect(detail).not.toContainText('Resultados ainda não publicados');
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: calendar independently loads packed company dates before Market is opened', async ({ page }) => {
  await page.route('**/data/stocks-startup.json', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      layout: 'field_rows_v1',
      fields: ['ticker', 'name', 'quote_type', 'market_cap', 'analyst_next_earnings_date'],
      rows: [['TESTCO', 'Test Company', 'EQUITY', 1000000000, '2026-10-13']],
    }),
  }));
  await page.route('**/data/macro-events.json', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ events: [] }),
  }));
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  await expect.poll(async () => page.evaluate(() => {
    window.VestraWeeklyEvents.render({ now: new Date(2026, 9, 12, 12, 0, 0), macroEvents: { events: [] } });
    return document.querySelector('#dashboardWeeklyEventsCard')?.textContent?.includes('TESTCO');
  }), { timeout: 15000 }).toBe(true);
  const card = page.locator('#dashboardWeeklyEventsCard');
  await expect(card).toContainText('Test Company');
  await expect(card).not.toContainText('Cobertura de resultados: índice de empresas ainda indisponível');
  await expect(card).not.toContainText('O calendário depende das datas disponíveis');
});


test('iPhone/WebKit: archived prior-quarter earnings and future earnings remain visible after late archive load', async ({ page }) => {
  await page.route('**/data/earnings-events.json', async route => {
    await new Promise(resolve => setTimeout(resolve, 150));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema: 'vestra_earnings_events_v1',
        events: [
          { kind: 'earnings', ticker: 'HIST', name: 'Historical Company', date: '2026-09-02', analyst_latest_eps_actual: 2.1 },
          { kind: 'earnings', ticker: 'HIST', name: 'Historical Company', date: '2026-09-02', analyst_latest_eps_actual: 2.1 }
        ]
      })
    });
  });
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  await page.evaluate(() => document.getElementById('viewDashboard')?.classList.remove('dash-secondary-open'));
  await page.evaluate(async () => {
    await window.VestraWeeklyEvents.loadEarningsArchive();
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 2, 12),
      stocks: [{ ticker:'FUT', name:'Future Company', quote_type:'EQUITY', analyst_next_earnings_date:'2026-10-20' }],
      portfolioTickers: new Set(['HIST']),
      macroEvents: { events: [] }
    });
  });
  const card = page.locator('#dashboardWeeklyEventsCard');
  await expect.poll(async () => page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 2, 12),
      stocks: [{ ticker:'FUT', name:'Future Company', quote_type:'EQUITY', analyst_next_earnings_date:'2026-10-20' }],
      portfolioTickers: new Set(['HIST']),
      macroEvents: { events: [] }
    });
    return document.querySelectorAll('#dashboardWeeklyEventsCard [data-weekly-event-index]').length;
  }), { timeout: 15000 }).toBe(1);
  await expect(card).toContainText('Historical Company');
  await expect(card).toContainText('HIST');
  await page.evaluate(() => window.VestraWeeklyEvents.render({
    now: new Date(2026, 9, 20, 12),
    stocks: [{ ticker:'FUT', name:'Future Company', quote_type:'EQUITY', analyst_next_earnings_date:'2026-10-20' }],
    macroEvents: { events: [] }
  }));
  await expect(card).toContainText('Future Company');
  await expect(card).not.toContainText('Historical Company');
});

test('iPhone/WebKit: confirmed archive result upgrades stale same-day calendar without losing its metadata', async ({ page }) => {
  await page.route('**/data/earnings-events.json', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ schema: 'vestra_earnings_events_v1', events: [{
      kind: 'earnings', ticker: 'JNJ', name: 'Johnson & Johnson',
      date: '2026-10-13', analyst_latest_eps_actual: 2.25,
      analyst_latest_eps_estimate: 2.10, analyst_latest_eps_surprise_pct: 0.0714286,
    }] }),
  }));
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  await page.waitForLoadState('networkidle', { timeout: 25000 });
  const merged = await page.evaluate(async () => {
    const archive = await window.VestraWeeklyEvents.loadEarningsArchive();
    return window.VestraWeeklyEvents.combineArchivedStocks([{
      ticker: 'JNJ', name: 'Johnson & Johnson', quote_type: 'EQUITY',
      market_cap: 500000000000, analyst_latest_earnings_date: '2026-10-13',
      analyst_latest_eps_actual: null,
    }], archive);
  });
  expect(merged).toHaveLength(1);
  expect(merged[0].analyst_latest_eps_actual).toBe(2.25);
  expect(merged[0].market_cap).toBe(500000000000);
  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026,9,17), portfolioTickers: new Set(),
      stocks: [{ticker:'JNJ',name:'Johnson & Johnson',quote_type:'EQUITY',
        market_cap:500000000000, analyst_latest_earnings_date:'2026-10-13'}],
      macroEvents:{events:[]},
    });
  });
  // The reconciliation itself is exercised above; the interface must remain readable.
  const card = page.locator('#dashboardWeeklyEventsCard');
  await expect(card).toBeVisible();
  await expect(card.locator('.weekly-events-title')).toBeVisible();
});

test('iPhone/WebKit: published FOMC stays in weekly rail and readable after opening results', async ({page}) => {
  const fomc = {
    date:'2026-10-28',title:'FOMC · decisão de política monetária',short_title:'FOMC',
    category:'central_bank',region:'EUA',importance:'critical',source:'fed',
    result_status:'official_release_summary',result_released_at:'2026-10-28',
    result_summary:'Intervalo-alvo dos Fed funds: 3,75% a 4,00%.',
    result_metric_schema:'fed_funds_target_v1',
    result_metrics:{target_lower_pct:3.75,target_upper_pct:4.0},
    source_url:'https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm'
  };
  await page.route('**/data/macro-events.json', route => route.fulfill({
    status:200,contentType:'application/json',
    body:JSON.stringify({schema_version:2,generated_at:'2026-10-29T10:16:13Z',events:[fomc]})
  }));
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  await page.waitForLoadState('networkidle',{timeout:25000});
  await page.evaluate((row) => window.VestraWeeklyEvents.render({
    now:new Date(2026,9,29,10),stocks:[],portfolioTickers:new Set(),
    macroEvents:{events:[row]}
  }),fomc);
  const card=page.locator('#dashboardWeeklyEventsCard');
  const fomcEvent=card.locator('[data-weekly-event-index]').filter({hasText:'FOMC'});
  await expect(fomcEvent).toBeVisible();
  await fomcEvent.click();
  const detail=page.locator('#dashboardWeeklyEventDetail');
  await expect(detail).toBeVisible();
  await expect(detail).toContainText('3,75%');
  await expect(detail).toContainText('4,00%');
  // Clicking refreshes the feed asynchronously; the selected catalyst must survive.
  await expect.poll(async()=>fomcEvent.count()).toBe(1);
  await expect(detail).toBeVisible();
  await expect(detail).toContainText('Fed funds');
  await expect(card.locator('.weekly-events-range')).toContainText('out');
});
