const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: history is compact and Dashboard fills the passive-income grid with a 30-day dividend insight', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraDashboardUiRefresh));

  await page.evaluate(() => {
    try {
      // Keep the Dashboard out of its intentional first-run empty state and
      // provide one known upcoming payment backed by a real historical net
      // dividend for the same canonical ticker.
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const payDate = tomorrow.toISOString().slice(0, 10);
      state.assets = [{
        id: 'e2e-dashboard-dividend',
        name: 'E2E Dividend Asset',
        ticker: 'E2EDIV',
        yahooTicker: 'E2EDIV',
        type: 'stock',
        class: 'Ações',
        value: 725000,
        currency: 'EUR',
        _yahooDiv: { payDate, rate: 2.4, currency: 'EUR' },
      }];
      state.dividends = [{
        id: 'e2e-dividend-history',
        assetId: 'e2e-dashboard-dividend',
        assetName: 'E2E Dividend Asset',
        grossAmount: 50,
        taxWithheld: 8,
        netAmount: 42,
        date: '2026-08-15',
        notes: 'Ticker=E2EDIV · Yahoo=E2EDIV',
      }];
      state.history = [
        { dateISO:'2026-08-01', net:700000, assets:790000, liabilities:90000, passiveAnnual:15000, auto:true },
        { dateISO:'2026-08-07', net:710000, assets:800000, liabilities:90000, passiveAnnual:15100, auto:true },
        { dateISO:'2026-08-31', net:740000, assets:830000, liabilities:90000, passiveAnnual:16000, auto:true },
        { dateISO:'2026-09-06', net:725000, assets:815000, liabilities:90000, passiveAnnual:15800, auto:true },
      ];
      if (typeof renderDashboard === 'function') renderDashboard();
    } catch (_) {}
    document.getElementById('viewDashboard')?.classList.add('dash-secondary-open');
    window.VestraDashboardUiRefresh.refresh();
  });

  const pulse = page.locator('#dashboardPortfolioPulseCard');
  await expect(pulse).toBeVisible({ timeout: 15_000 });
  await expect(pulse).toContainText('Pulso patrimonial');
  await expect(pulse).toContainText('7 dias');
  await expect(pulse).toContainText('30 dias');
  await expect(pulse).toContainText('Máximo 90d');

  const upcoming = page.locator('#dashboardUpcomingDividendsTile');
  await expect(upcoming).toBeVisible();
  await expect(upcoming).toContainText('Próximos 30 dias');
  await expect(upcoming).toContainText('42');
  await expect(upcoming).toContainText('1 pagamento previsto');
  // The base Dashboard contains four quick KPI cells; this insight deliberately
  // fills the previously empty fifth slot rather than creating a sixth tile.
  await expect(page.locator('#viewDashboard .kpi-quick__grid > .kpi-quick__cell')).toHaveCount(5);

  const summary = page.locator('#snapshotHistorySummary');
  const table = page.locator('#snapshotTable');
  await expect(summary).toBeVisible();
  await expect(summary).toContainText('Histórico diário');
  await expect(summary.locator('button')).toContainText('Ver histórico');
  await expect(table).toBeHidden();

  await summary.locator('button').click();
  await expect(table).toBeVisible();
  await expect(summary.locator('button')).toHaveText('Fechar');

  await summary.locator('button').click();
  await expect(table).toBeHidden();
  await expect(summary.locator('button')).toContainText('Ver histórico');

  await expect(page.locator('#navCashflow .navico')).toHaveText('↕︎');
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: Dashboard shows a clean empty upcoming state and integrates the negative TWR warning as a health card', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.goto('/index.html');
  await page.waitForFunction(() => window.VestraDashboardUiRefresh?.version === '1.1');

  await page.evaluate(() => {
    state.assets = [{ id:'e2e-cash', name:'Cash', type:'cash', class:'Depósitos', value:1000, currency:'EUR' }];
    state.dividends = [];
    if (typeof renderDashboard === 'function') renderDashboard();
    window.calcTWR = () => ({ annualised: -25.9, years: 1 });
    const alert = document.getElementById('negReturnAlert');
    alert.style.display = '';
    window.VestraDashboardUiRefresh.refresh();
  });

  const upcoming = page.locator('#dashboardUpcomingDividendsTile');
  await expect(upcoming).toContainText('—');
  await expect(upcoming).toContainText('sem pagamentos previstos');

  const health = page.locator('#negReturnAlert.dashboard-health-card');
  await expect(health).toBeVisible();
  await expect(health).toContainText('Saúde do património');
  await expect(health).toContainText('TWR anualizado -25,9%/ano');
  await expect(health).toContainText('Abaixo da inflação');
  await expect(health).not.toContainText('⚠️');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});