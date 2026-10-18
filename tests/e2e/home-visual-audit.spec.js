const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Preserve real rendered evidence after a green WebKit run as well as failures.
test('iPhone/WebKit: Intelligence Home responsive evidence at phone and desktop widths', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({ timeout: 20000 });
  const out = path.join('test-results', 'visual-evidence');
  fs.mkdirSync(out, { recursive: true });

  for (const viewport of [
    { name: 'iphone-390', width: 390, height: 844 },
    { name: 'desktop-1280', width: 1280, height: 800 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.waitForTimeout(350);
    const home = page.locator('#vestraIntelligenceHome');
    const actions = home.locator('.vi-priorities .vi-action');
    await expect(actions).toHaveCount(3);
    await expect(actions.first()).toBeVisible();
    const measures = await page.evaluate(() => {
      const host = document.getElementById('vestraIntelligenceHome');
      const rows = Array.from(host.querySelectorAll('.vi-priorities .vi-action'));
      const rectangles = rows.map(e => e.getBoundingClientRect());
      const opening = host.querySelector('.vi-home-overview > .vi-opening')?.getBoundingClientRect();
      const priorities = host.querySelector('.vi-home-overview > .vi-priorities')?.getBoundingClientRect();
      const overview = host.querySelector('.vi-home-overview')?.getBoundingClientRect();
      const wealth = host.querySelector('.vi-wealth')?.getBoundingClientRect();
      const lead = host.querySelector('.vi-opening > .vi-lead')?.getBoundingClientRect();
      return {
        width: document.documentElement.clientWidth,
        hostWidth: host.getBoundingClientRect().width,
        documentWidth: document.documentElement.scrollWidth,
        hostScrollWidth: host.scrollWidth,
        hostClientWidth: host.clientWidth,
        lefts: rectangles.map(r => Math.round(r.left)),
        openingLeft: opening ? Math.round(opening.left) : null,
        overviewWidth: overview?.width ?? 0,
        openingWidth: opening?.width ?? 0,
        leadWidth: lead?.width ?? 0,
        wealthWidth: wealth?.width ?? 0,
        openingTop: opening ? Math.round(opening.top) : null,
        prioritiesLeft: priorities ? Math.round(priorities.left) : null,
        prioritiesTop: priorities ? Math.round(priorities.top) : null,
        tops: rectangles.map(r => Math.round(r.top)),
        overflow: rows.some(e => e.scrollWidth > e.clientWidth + 3),
        offenders: Array.from(document.querySelectorAll('body *'))
          .filter(e => {
            const style = getComputedStyle(e);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const r = e.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && (r.right > innerWidth + 4 || r.left < -4);
          })
          .sort((a,b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)
          .slice(0,20)
          .map(e => {
            const r=e.getBoundingClientRect();
            return { tag:e.tagName, id:e.id, className:String(e.className).slice(0,120),
              left:Math.round(r.left), right:Math.round(r.right), width:Math.round(r.width) };
          }),
      };
    });
    fs.writeFileSync(path.join(out, 'layout-' + viewport.name + '.json'), JSON.stringify(measures, null, 2));
    await home.screenshot({ path: path.join(out, 'intelligence-' + viewport.name + '.png'), animations: 'disabled' });
    await page.screenshot({ path: path.join(out, 'page-' + viewport.name + '.png'), fullPage: true, animations: 'disabled' });
    expect(measures.documentWidth).toBeLessThanOrEqual(viewport.width + 3);
    expect(measures.hostScrollWidth).toBeLessThanOrEqual(measures.hostClientWidth + 3);
    expect(measures.overflow).toBe(false);
    if (viewport.width < 600) {
      // The entire reading and wealth area must fill its available Home column.
      expect(measures.openingWidth).toBeGreaterThan(measures.overviewWidth - 5);
      expect(measures.leadWidth).toBeGreaterThan(measures.openingWidth - 5);
      expect(measures.wealthWidth).toBeGreaterThan(measures.leadWidth - 5);
      expect(measures.tops[1]).toBeGreaterThan(measures.tops[0]);
      expect(measures.tops[2]).toBeGreaterThan(measures.tops[1]);
    } else {
      // The editorial composition places investigations vertically beside the opening.
      expect(measures.tops[1]).toBeGreaterThan(measures.tops[0]);
      expect(measures.tops[2]).toBeGreaterThan(measures.tops[1]);
      expect(Math.abs(measures.lefts[1] - measures.lefts[0])).toBeLessThan(8);
      expect(Math.abs(measures.lefts[2] - measures.lefts[0])).toBeLessThan(8);
      expect(measures.prioritiesLeft).toBeGreaterThan(measures.openingLeft);
      expect(Math.abs(measures.prioritiesTop - measures.openingTop)).toBeLessThan(8);
    }
  }
  // Expanded patrimony: verify the text actually rendered on dark cards is legible.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#vestraIntelligenceHome button[data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toBeVisible();
  const readings = await page.evaluate(() => {
    const selectors = [
      '.v2-home-section-label h2',
      '.v2-home-secondary-hub__intro h3',
      '.v2-detail-history > summary > strong',
      '.v2-detail-history__hint',
    ];
    return selectors.map(selector => {
      const el = document.querySelector('#viewDashboard ' + selector);
      if (!el) return { selector, missing: true };
      const style = getComputedStyle(el);
      return { selector, missing: false, color: style.color,
        fill: style.webkitTextFillColor, opacity: Number(style.opacity) };
    });
  });
  fs.writeFileSync(path.join(out, 'patrimony-contrast-iphone.json'), JSON.stringify(readings, null, 2));
  for (const item of readings) {
    expect(item.missing, item.selector).toBe(false);
    expect(item.opacity, item.selector).toBeGreaterThanOrEqual(0.99);
    // Expect explicitly bright ink instead of inherited navy on the dark stage.
    const rgb = item.fill.match(/\\d+/g)?.slice(0, 3).map(Number) || [];
    expect(rgb.length, item.selector).toBe(3);
    expect(Math.min(...rgb), item.selector).toBeGreaterThanOrEqual(155);
  }
  expect(errors).toEqual([]);
});
