const { test, expect } = require('@playwright/test');

// The normal functional suite deliberately blocks service workers to keep UI
// regressions deterministic. This spec is the explicit PWA integration gate.
test.use({ serviceWorkers: 'allow' });

test('iPhone/WebKit: installed PWA runtime gains a service-worker controller and safe update ownership', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html', { waitUntil: 'load' });
  await page.waitForFunction(() => 'serviceWorker' in navigator);

  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });

  // skipWaiting + clients.claim should make the first loaded client controlled.
  // Allow WebKit a short lifecycle turn; if it still is not controlled, one reload
  // is legitimate and mirrors opening an already-installed PWA again.
  try {
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 5_000 });
  } catch (_) {
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 10_000 });
  }

  const pwa = await page.evaluate(async () => {
    const registration = await navigator.serviceWorker.getRegistration();
    const cacheNames = await caches.keys();
    const vestraCacheName = cacheNames.find(name => name.startsWith('vestra-cache-')) || '';
    const cache = vestraCacheName ? await caches.open(vestraCacheName) : null;
    const cachedUrls = cache ? (await cache.keys()).map(request => new URL(request.url).pathname.split('/').pop()) : [];
    const updateButton = document.getElementById('btnForceUpdate');
    return {
      controlled: Boolean(navigator.serviceWorker.controller),
      scriptURL: registration?.active?.scriptURL || registration?.waiting?.scriptURL || registration?.installing?.scriptURL || '',
      cacheName: vestraCacheName,
      hasAppShell: cachedUrls.includes('app.js'),
      hasMarketRuntime: cachedUrls.includes('market-analysis-tools-runtime.js'),
      updateManagerVersion: window.VestraAppUpdateManager?.version || '',
      safeUpdateOwner: updateButton?.dataset?.vestraSafeUpdateOwner || '',
    };
  });

  expect(pwa.controlled).toBeTruthy();
  expect(pwa.scriptURL).toContain('/sw.js');
  expect(pwa.cacheName).toMatch(/^vestra-cache-/);
  expect(pwa.hasAppShell).toBeTruthy();
  expect(pwa.hasMarketRuntime).toBeTruthy();
  expect(pwa.updateManagerVersion).toBe('1.3');
  expect(pwa.safeUpdateOwner).toBe('1');
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
