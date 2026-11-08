const { test, expect } = require('@playwright/test');

test.use({ serviceWorkers: 'block' });

test('iPhone/WebKit: dividend and analysis editorial headings keep readable text on light surfaces', async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  for(const name of ['dividends','analysis']){
    await page.evaluate(view => setView(view), name);
    const hero = page.locator('#view'+name[0].toUpperCase()+name.slice(1)+' .view-intro');
    await expect(hero).toBeVisible();
    const styles = await hero.evaluate(el => {
      const text=el.querySelector('p'),heading=el.querySelector('h2'),kicker=el.querySelector('.view-intro__eyebrow');
      return {desc:getComputedStyle(text).color,heading:getComputedStyle(heading).color,
        kicker:getComputedStyle(kicker).color,bodyFont:parseFloat(getComputedStyle(text).fontSize),
        bg:getComputedStyle(el).backgroundImage};
    });
    expect(styles.desc).toBe('rgb(61, 87, 90)');
    expect(styles.heading).toBe('rgb(23, 52, 59)');
    expect(styles.bodyFont).toBeGreaterThanOrEqual(13);
    expect(styles.bg).toContain('linear-gradient');
  }
});

test('iPhone/WebKit: analysis tab rails scroll with content rather than mask charts', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  await page.evaluate(() => setView('analysis'));
  await expect(page.locator('#analysisTabs')).toBeVisible();
  const rail = await page.locator('#viewAnalysis .analysis-tabs-wrap').evaluate(el=>({
    position:getComputedStyle(el).position,
    overflow:getComputedStyle(el).overflow,
    width:el.getBoundingClientRect().width,
    viewport:document.documentElement.clientWidth,
  }));
  expect(rail.position).not.toBe('sticky');
  expect(rail.width).toBeLessThanOrEqual(rail.viewport+1);
  const sub = page.locator('#portfolioSubTabs');
  await expect(sub).toBeVisible();
  expect(await sub.evaluate(el=>getComputedStyle(el).position)).not.toBe('sticky');
  const bottom = await page.locator('.main').evaluate(el=>parseFloat(getComputedStyle(el).paddingBottom));
  expect(bottom).toBeGreaterThanOrEqual(110);
});

test('iPhone/WebKit: sector dossier action moves below the name with a comfortable touch area', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  await page.evaluate(() => {
    setView('assets');
    const outer=document.querySelector('#portfolioSectorBody');
    if(!outer)throw new Error('Missing canonical portfolio sector host');
    const group=document.createElement('details');
    group.className='portfolio-sector-group';
    group.open=true;
    group.innerHTML='<summary><span class="portfolio-sector-title"><strong>Tecnologia</strong></span></summary><div class="portfolio-sector-assets"><div class="portfolio-sector-asset"><div class="portfolio-sector-asset__main"><strong>Exemplo de empresa de tecnologia com nome longo</strong><span>TEST · 12.5% do sector</span></div><div class="portfolio-sector-asset__metrics"><strong>1 225 €</strong><span>0.8% ações + ETFs · +6.4%</span></div><button type="button" class="portfolio-sector-research">Dossier ↗</button></div></div>';
    outer.appendChild(group);
    const disclosure=document.querySelector('#portfolioSectorCard');
    if(disclosure)disclosure.open=true;
    document.querySelector('#portfolioToolsStrip').open=true;
  });
  const entry=page.locator('#portfolioSectorBody .portfolio-sector-asset').last();
  await expect(entry).toBeVisible();
  const info=await entry.evaluate(el => {
    const name=el.querySelector('.portfolio-sector-asset__main').getBoundingClientRect();
    const metrics=el.querySelector('.portfolio-sector-asset__metrics').getBoundingClientRect();
    const btn=el.querySelector('.portfolio-sector-research').getBoundingClientRect();
    return {nameBottom:name.bottom,metricsTop:metrics.top,btnTop:btn.top,
      btnWidth:btn.width,btnHeight:btn.height,overflow:el.scrollWidth-el.clientWidth};
  });
  expect(info.metricsTop).toBeGreaterThanOrEqual(info.nameBottom-2);
  expect(info.btnTop).toBeGreaterThanOrEqual(info.nameBottom-2);
  expect(info.btnHeight).toBeGreaterThanOrEqual(44);
  expect(info.overflow).toBeLessThanOrEqual(1);
});
