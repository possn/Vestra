const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Home headings and drawer chrome have accessible foreground contrast', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => document.querySelector('#vestraIntelligenceHome')?.offsetWidth > 0);
  const inspect = async selector => page.locator(selector).first().evaluate(el => {
    const rgb = value => {
      const match = value.match(/rgba?\(([^)]+)\)/);
      return match ? match[1].split(',').slice(0, 3).map(Number) : null;
    };
    const luminance = channels => {
      const linear = channels.map(n => {
        const c = n / 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return linear[0] * .2126 + linear[1] * .7152 + linear[2] * .0722;
    };
    const styles = getComputedStyle(el);
    const foreground = rgb(styles.color);
    let parent = el;
    let background = null;
    while (parent && !background) {
      const css = getComputedStyle(parent);
      const value = css.backgroundColor;
      const rgba = value.match(/rgba?\(([^)]+)\)/);
      if (rgba) {
        const parts = rgba[1].split(',').map(Number);
        if (parts.length === 3 || parts[3] >= .99) background = rgb(value);
      }
      parent = parent.parentElement;
    }
    if (!foreground || !background) return { ratio: 0, foreground, background };
    const a = luminance(foreground), b = luminance(background);
    return { ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05), foreground, background };
  });
  const title = await inspect('#vestraIntelligenceHome .vi-headline');
  const deck = await inspect('#vestraIntelligenceHome .vi-deck');
  expect(title.ratio, JSON.stringify(title)).toBeGreaterThanOrEqual(4.5);
  expect(deck.ratio, JSON.stringify(deck)).toBeGreaterThanOrEqual(4.5);

  await page.locator('#btnSidebarToggle').click();
  await expect(page.locator('#sidebar')).toHaveClass(/sidebar--open/);
  const titleInDrawer = await inspect('.sidebar__title');
  expect(titleInDrawer.ratio, JSON.stringify(titleInDrawer)).toBeGreaterThanOrEqual(4.5);
});

test('iPhone/WebKit: drawer and bottom navigation share five canonical destinations', async ({ page }) => {
  await page.goto('/index.html');
  const destinations = [
    ['dashboard', 'Início'], ['assets', 'Carteira'], ['market', 'Mercado'],
    ['cashflow', 'Fluxos'], ['settings', 'Mais']
  ];
  for (const [route, label] of destinations) {
    await expect(page.locator(`.bottomnav [data-view="${route}"] .navlbl`)).toHaveText(label);
    await expect(page.locator(`#sidebar [data-view="${route}"] span:last-child`)).toHaveText(label);
  }
  for (const route of ['dividends', 'analysis']) {
    await expect(page.locator(`#sidebar [data-view="${route}"]`)).toHaveCount(1);
  }
});
