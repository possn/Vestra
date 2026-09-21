const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: service worker installs, controls reload and caches bootstrap shell', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html', { waitUntil: 'load' });
  await expect.poll(
    () => page.evaluate(() => 'serviceWorker' in navigator),
    { timeout: 10_000 }
  ).toBe(true);

  const registration = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.ready;
    return {
      active: Boolean(reg.active),
      scriptURL: reg.active?.scriptURL || ''
    };
  });
  expect(registration.active).toBe(true);
  expect(registration.scriptURL).toContain('/sw.js');

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(navigator.serviceWorker?.controller), null, { timeout: 15_000 });

  const cacheState = await page.evaluate(async () => {
    const keys = await caches.keys();
    const vestra = keys.filter(key => /^vestra-cache-v\d+$/.test(key));
    const latest = vestra.at(-1) || '';
    const cache = latest ? await caches.open(latest) : null;
    const required = ['./index.html', './styles.css', './app.js', './app-ui-core.js'];
    const hits = {};
    for (const asset of required) {
      hits[asset] = Boolean(cache && await cache.match(asset, { ignoreSearch: true }));
    }
    return {
      controller: Boolean(navigator.serviceWorker.controller),
      cacheNames: vestra,
      hits
    };
  });

  expect(cacheState.controller).toBe(true);
  expect(cacheState.cacheNames.length).toBeGreaterThan(0);
  for (const [asset, hit] of Object.entries(cacheState.hits)) {
    expect(hit, `required app-shell asset not cached: ${asset}`).toBe(true);
  }

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
