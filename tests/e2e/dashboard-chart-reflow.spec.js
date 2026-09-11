const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: dashboard charts fill their cards after render and viewport reflow', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraUiCore?.scheduleChartStabilization));

  await page.evaluate(() => {
    state.assets = [
      { id:'chart-a', name:'Chart A', type:'stock', class:'Ações', value:500000, currency:'EUR' },
      { id:'chart-b', name:'Chart B', type:'cash', class:'Depósitos', value:200000, currency:'EUR' },
    ];
    state.liabilities = [];
    state.history = [
      { dateISO:'2026-08-01', net:650000, assets:650000, liabilities:0, passiveAnnual:0, auto:true },
      { dateISO:'2026-08-15', net:675000, assets:675000, liabilities:0, passiveAnnual:0, auto:true },
      { dateISO:'2026-09-01', net:690000, assets:690000, liabilities:0, passiveAnnual:0, auto:true },
      { dateISO:'2026-09-11', net:700000, assets:700000, liabilities:0, passiveAnnual:0, auto:true },
    ];
    if (typeof renderDashboard === 'function') renderDashboard();
    window.VestraUiCore.scheduleChartStabilization(document);
  });

  await page.waitForTimeout(550);

  const initial = await page.locator('#viewDashboard .chartWrap canvas:visible').evaluateAll(canvases => canvases.map(canvas => {
    const wrap = canvas.closest('.chartWrap');
    return {
      canvasWidth: canvas.getBoundingClientRect().width,
      wrapWidth: wrap?.getBoundingClientRect().width || 0,
      bitmapWidth: canvas.width,
    };
  }));

  expect(initial.length).toBeGreaterThanOrEqual(2);
  for (const item of initial) {
    expect(item.wrapWidth).toBeGreaterThan(250);
    expect(item.canvasWidth / item.wrapWidth).toBeGreaterThan(0.92);
    expect(item.bitmapWidth).toBeGreaterThan(250);
  }

  await page.setViewportSize({ width: 390, height: 720 });
  await page.evaluate(() => {
    window.dispatchEvent(new Event('resize'));
    window.VestraUiCore.scheduleChartStabilization(document);
  });
  await page.waitForTimeout(550);

  const after = await page.locator('#viewDashboard .chartWrap canvas:visible').evaluateAll(canvases => canvases.map(canvas => {
    const wrap = canvas.closest('.chartWrap');
    return {
      canvasWidth: canvas.getBoundingClientRect().width,
      wrapWidth: wrap?.getBoundingClientRect().width || 0,
      bitmapWidth: canvas.width,
    };
  }));

  expect(after.length).toBeGreaterThanOrEqual(2);
  for (const item of after) {
    expect(item.canvasWidth / item.wrapWidth).toBeGreaterThan(0.92);
    expect(item.bitmapWidth).toBeGreaterThan(250);
  }

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});