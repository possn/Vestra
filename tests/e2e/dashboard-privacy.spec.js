const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: portfolio privacy toggles immediately without a Dashboard rerender', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.toggleDashboardPrivacy === 'function');

  await page.evaluate(() => {
    if (!state.settings) state.settings = {};
    state.settings.hideDashboardValues = false;
    state.assets = [{
      id: 'privacy-e2e',
      name: 'Privacy test',
      type: 'cash',
      class: 'Depósitos',
      value: 12345,
      currency: 'EUR',
    }];
    state.liabilities = [];
    if (typeof renderDashboard === 'function') renderDashboard();

    window.__privacyRenderCalls = 0;
    const originalRenderDashboard = window.renderDashboard;
    window.renderDashboard = (...args) => {
      window.__privacyRenderCalls += 1;
      return originalRenderDashboard(...args);
    };
  });

  const button = page.locator('#btnDashboardPrivacy');
  const net = page.locator('#kpiNet');

  await expect(button).toContainText('Ocultar valores');
  await expect(net).toContainText('€');

  await button.click();
  await expect(button).toContainText('Mostrar valores');
  await expect(button).toHaveAttribute('aria-pressed', 'true');
  await expect(net).toContainText('•••• €');
  expect(await page.evaluate(() => window.__privacyRenderCalls)).toBe(0);

  await button.click();
  await expect(button).toContainText('Ocultar valores');
  await expect(button).toHaveAttribute('aria-pressed', 'false');
  await expect(net).not.toContainText('••••');
  await expect(net).toContainText('12');
  expect(await page.evaluate(() => window.__privacyRenderCalls)).toBe(0);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
