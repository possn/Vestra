const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash wordmark stays readable and no empty KPI quadrant appears', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({ timeout: 20000 });
  const splash = await page.locator('#appLoadingOverlay .vestra-splash__brand').evaluate(el => {
    const style = getComputedStyle(el);
    return { color: style.color, fill: style.webkitTextFillColor };
  });
  // Splash is a light-ink mark on a very dark green background.
  for (const value of [splash.color, splash.fill]) {
    const rgb = String(value).match(/[0-9]+/g)?.slice(0, 3).map(Number);
    expect(rgb?.length).toBe(3);
    expect(Math.min(...rgb)).toBeGreaterThan(185);
  }
  await page.locator('#vestraIntelligenceHome button[data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
  const layout = await page.locator('#viewDashboard .kpi-quick__cell--purple').evaluate(el => {
    const style = getComputedStyle(el);
    return { column: style.gridColumnStart, end: style.gridColumnEnd };
  });
  expect(layout.column).toBe('1');
  expect(layout.end).toBe('-1');
});

test('iPhone/WebKit: Home daily brief separates source event and news fields', async ({ page }) => {
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({ timeout: 20000 });
  await page.evaluate(() => {
    const list = document.querySelector('#dashboardWeeklyEventsCard .weekly-events-list');
    const news = document.querySelector('#vestraDailyNewsCard');
    if (!list || !news) throw new Error('canonical source unavailable');
    list.innerHTML = '<button class="weekly-event" data-weekly-event-date="2099-10-18"><div class="weekly-event__day">Amanhã</div><div class="weekly-event__ticker">TEST</div><div class="weekly-event__name">Empresa Exemplo</div><div class="weekly-event__type">Resultados</div></button>';
    const article = news.querySelector('.vestra-daily-news-item');
    if (!article) throw new Error('news source unavailable');
    article.innerHTML = '<span class="vestra-daily-news-badge">MERCADO</span><strong>Notícia de exemplo</strong><small>Fonte · há 1 h</small>';
    window.dispatchEvent(new Event('focus'));
  });
  await expect(page.locator('[data-vi-canonical-event-list]')).toContainText('TEST');
  await expect(page.locator('[data-vi-canonical-event-list]')).toContainText('Empresa Exemplo');
  await expect(page.locator('[data-vi-canonical-news-list]')).toContainText('Notícia de exemplo');
});
