const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: history is compact by default and Dashboard shows portfolio pulse', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraDashboardUiRefresh));

  await page.evaluate(() => {
    try {
      state.history = [
        { dateISO:'2026-08-01', net:700000, assets:790000, liabilities:90000, passiveAnnual:15000, auto:true },
        { dateISO:'2026-08-07', net:710000, assets:800000, liabilities:90000, passiveAnnual:15100, auto:true },
        { dateISO:'2026-08-31', net:740000, assets:830000, liabilities:90000, passiveAnnual:16000, auto:true },
        { dateISO:'2026-09-06', net:725000, assets:815000, liabilities:90000, passiveAnnual:15800, auto:true },
      ];
      if (typeof renderDashboard === 'function') renderDashboard();
    } catch (_) {}
    window.VestraDashboardUiRefresh.refresh();
  });

  const pulse = page.locator('#dashboardPortfolioPulseCard');
  await expect(pulse).toBeVisible({ timeout: 15_000 });
  await expect(pulse).toContainText('Pulso patrimonial');
  await expect(pulse).toContainText('7 dias');
  await expect(pulse).toContainText('30 dias');
  await expect(pulse).toContainText('Máximo 90d');

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
