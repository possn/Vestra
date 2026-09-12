const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard renders weekly macro catalysts plus portfolio earnings', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));

  // Reproduce the real default Dashboard state: secondary cards are collapsed.
  await page.evaluate(() => document.getElementById('viewDashboard')?.classList.remove('dash-secondary-open'));

  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 6, 9, 0, 0),
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
  await expect(card.locator('.weekly-events-range')).toHaveText('6/09 – 12/09');

  // Weekly cards now use an index because the first tap opens the event detail;
  // ticker identity is carried by the dossier action inside an earnings detail.
  const events = card.locator('[data-weekly-event-index]');
  await expect(events).toHaveCount(4);
  await expect(events.nth(0)).toContainText('NVDA');
  await expect(events.nth(0)).toContainText('NVIDIA Corporation');
  await expect(events.nth(0)).toContainText('No portefólio');
  await expect(events.nth(1)).toContainText('AAPL');
  await expect(events.nth(1)).toContainText('Apple Inc.');
  await expect(events.nth(2)).toContainText('PPI EUA');
  await expect(events.nth(3)).toContainText('CPI EUA');
  await expect(card).toContainText('Inflação');
  await expect(card).toContainText('Impacto elevado');
  await expect(card).not.toContainText('FOMC');
  await expect(card).not.toContainText('ETF1');

  await events.nth(0).click();
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
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));

  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 11, 14, 0, 0),
      portfolioTickers: new Set(),
      stocks: [],
      macroEvents: {
        events: [{
          date:'2026-09-11',
          short_title:'CPI EUA',
          title:'CPI EUA',
          category:'inflation',
          region:'EUA',
          importance:'high',
          source:'bls',
          time_local:'7:30 AM CT',
          result_status:'official_release_summary',
          result_summary:'BLS Public Data API · August 2026: headline +0.4% MoM / +3.4% YoY; core +0.3% MoM / +2.4% YoY.',
          result_released_at:'2026-09-11',
          result_metric_schema:'bls_cpi_v1',
          result_metrics:{ headline_mom_pct:0.4, headline_yoy_pct:3.4, core_mom_pct:0.3, core_yoy_pct:2.4 },
          result_transport:'bls_public_api',
          source_url:'https://www.bls.gov/news.release/cpi.nr0.htm',
        }]
      }
    });
  });

  const event = page.locator('#dashboardWeeklyEventsCard [data-weekly-event-index]').first();
  await expect(event).toContainText('CPI EUA');
  await event.click();

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
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: reported company earnings replace a stale pending event on the same date', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));

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
