const { test, expect } = require('@playwright/test');

// The normal functional suite deliberately blocks service workers to keep UI
// regressions deterministic. This spec is the explicit PWA integration gate.
test.use({ serviceWorkers: 'allow' });

async function readPwaState(page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await page.evaluate(async () => {
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
          safeUpdateApiReady: typeof window.VestraUiCore?.installSafeUpdateGuard === 'function' &&
            typeof window.VestraUiCore?.forceFreshReload === 'function',
          updateButtonPresent: Boolean(updateButton),
        };
      });
    } catch (error) {
      if (!/Execution context was destroyed|navigation/i.test(String(error?.message || error)) || attempt === 2) throw error;
      await page.waitForLoadState('load');
      await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 10_000 });
    }
  }
  throw new Error('Unable to read stable PWA runtime state');
}

test('iPhone/WebKit: installed PWA runtime gains a service-worker controller and safe update ownership', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html', { waitUntil: 'load' });
  await page.waitForFunction(() => 'serviceWorker' in navigator);

  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });

  // skipWaiting + clients.claim should make the client controlled without
  // restarting an active session. A controllerchange must never force a hidden
  // cache-busted navigation or replay the launch splash mid-use.
  try {
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 5_000 });
  } catch (_) {
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 10_000 });
  }

  const beforeControllerChangeUrl = page.url();
  await page.evaluate(() => {
    window.__vestraServiceWorkerUpdated = false;
    navigator.serviceWorker.dispatchEvent(new Event('controllerchange'));
  });
  await page.waitForTimeout(250);
  expect(page.url()).toBe(beforeControllerChangeUrl);
  expect(new URL(page.url()).searchParams.has('_sw')).toBeFalsy();
  await expect.poll(() => page.evaluate(() => window.__vestraServiceWorkerUpdated)).toBeTruthy();
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 10_000 });

  const pwa = await readPwaState(page);

  expect(pwa.controlled).toBeTruthy();
  expect(pwa.scriptURL).toContain('/sw.js');
  expect(pwa.cacheName).toMatch(/^vestra-cache-/);
  expect(pwa.hasAppShell).toBeTruthy();
  expect(pwa.hasMarketRuntime).toBeTruthy();
  expect(pwa.safeUpdateApiReady).toBeTruthy();
  expect(pwa.updateButtonPresent).toBeTruthy();

  // Prove the loaded UI-core capture guard owns the real update button in
  // WebKit: a target listener added after app bootstrap must never receive the
  // click. Returning false from confirm keeps this ownership probe navigation-free.
  const safeCaptureOwnsClick = await page.evaluate(() => {
    const button = document.getElementById('btnForceUpdate');
    if (!button) return false;
    let targetRan = false;
    const originalConfirm = window.confirm;
    window.confirm = () => false;
    button.addEventListener('click', () => { targetRan = true; }, { once: true });
    button.click();
    window.confirm = originalConfirm;
    return !targetRan;
  });
  expect(safeCaptureOwnsClick).toBeTruthy();

  expect(new URL(page.url()).searchParams.has('_sw')).toBeFalsy();

  // Controller takeover is deliberately navigation-free; keep every browser
  // error fatal now that no execution-context replacement is expected.
  const unexpectedPageErrors = pageErrors.filter(message => message !== 'Context is stopped');
  expect(unexpectedPageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});