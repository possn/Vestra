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

  const hiddenNow = await page.evaluate(() => {
    window.__privacyRenderCalls = 0;
    document.getElementById('btnDashboardPrivacy').click();
    return {
      renderCalls: window.__privacyRenderCalls,
      label: document.getElementById('dashboardPrivacyLabel').textContent,
      pressed: document.getElementById('btnDashboardPrivacy').getAttribute('aria-pressed'),
      net: document.getElementById('kpiNet').textContent,
    };
  });
  expect(hiddenNow.renderCalls).toBe(0);
  expect(hiddenNow.label).toContain('Mostrar valores');
  expect(hiddenNow.pressed).toBe('true');
  expect(hiddenNow.net).toContain('•••• €');

  const visibleNow = await page.evaluate(() => {
    window.__privacyRenderCalls = 0;
    document.getElementById('btnDashboardPrivacy').click();
    return {
      renderCalls: window.__privacyRenderCalls,
      label: document.getElementById('dashboardPrivacyLabel').textContent,
      pressed: document.getElementById('btnDashboardPrivacy').getAttribute('aria-pressed'),
      net: document.getElementById('kpiNet').textContent,
    };
  });
  expect(visibleNow.renderCalls).toBe(0);
  expect(visibleNow.label).toContain('Ocultar valores');
  expect(visibleNow.pressed).toBe('false');
  expect(visibleNow.net).not.toContain('••••');
  expect(visibleNow.net).toContain('12');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
