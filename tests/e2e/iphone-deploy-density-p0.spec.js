const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
test('PWA requests new compact generation and forbids cross-version CSS fallback',async({page})=>{
 await page.goto('/index.html');
 const links=await page.locator('link[rel="stylesheet"]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
 expect(links).toContain('vestra-iphone-canonical-scale.css?v=20261022-pre1386-visual');
 const sw=fs.readFileSync('sw.js','utf8');
 expect(sw).toMatch(/const CACHE_NAME = "vestra-cache-v\d+";/);
 expect(sw).toContain('if (new URL(request.url).search) return undefined');
});
test('iPhone actual Home and Portfolio compact geometry',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const values=await page.evaluate(()=>{
  const font=selector=>{const el=document.querySelector(selector);return el?parseFloat(getComputedStyle(el).fontSize):null};
  return {headline:font('#vestraIntelligenceHome .vi-headline'),
          chapter:font('#vestraIntelligenceHome .vi-section-top h3'),
          portfolio:font('#portfolioHeroTitle'),
          total:font('#portfolioTotalValue'),
          market:font('#viewMarket .market-hero-simple h2')};
 });
 for(const [key,limit] of Object.entries({headline:27,chapter:15,portfolio:27,total:30,market:29})){
  expect(values[key],key).not.toBeNull();
  expect(values[key],key).toBeLessThanOrEqual(limit);
 }
});

test('iPhone splash identity remains compact without zoom',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const css=await page.evaluate(()=>{
  const a=document.querySelector('.vestra-splash__mark');
  const b=document.querySelector('.vestra-splash__brand');
  const c=document.querySelector('.vestra-splash__tagline');
  return {mark:parseFloat(getComputedStyle(a).width),brand:parseFloat(getComputedStyle(b).fontSize),tagline:parseFloat(getComputedStyle(c).fontSize)};
 });
 expect(css.mark).toBeLessThanOrEqual(68);
 expect(css.brand).toBeLessThanOrEqual(33);
 expect(css.tagline).toBeLessThanOrEqual(10);
});

test('iPhone active Market route renders compact headline, search and tools',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 await expect(page.locator('#viewMarket')).toBeVisible();
 const sizes=await page.evaluate(()=>{
  const get=s=>{const el=document.querySelector(s);if(!el)return null;const st=getComputedStyle(el);return {size:parseFloat(st.fontSize),height:el.getBoundingClientRect().height};};
  return {hero:get('#viewMarket .market-hero-simple h2'),search:get('#viewMarket .market-search input')};
 });
 expect(sizes.hero).not.toBeNull();
 expect(sizes.hero.size).toBeLessThanOrEqual(26);
 expect(sizes.search).not.toBeNull();
 expect(sizes.search.size).toBeLessThanOrEqual(14);
 expect(sizes.search.height).toBeLessThanOrEqual(46);
});

test('Market filter rail remains within phone viewport and is scrollable to last mode',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 await expect(page.locator('#viewMarket')).toBeVisible();
 const rail=page.locator('#viewMarket .market-mode-grid').first();
 await expect(rail).toBeVisible();
 const widths=await rail.evaluate(el=>{const a=el.getBoundingClientRect();return {right:a.right,viewport:innerWidth,scroll:el.scrollWidth,client:el.clientWidth,overflow:getComputedStyle(el).overflowX};});
 expect(widths.right).toBeLessThanOrEqual(widths.viewport+2);
 expect(widths.overflow).toBe('auto');
 const last=rail.locator('.market-mode').last();
 await last.scrollIntoViewIfNeeded();
 await expect(last).toBeInViewport();
});


test('compact iPhone global rhythm does not zoom document or clip navigation',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const v=await page.evaluate(()=>{
  const get=el=>el.getBoundingClientRect();
  const nav=document.querySelector('.bottomnav');
  const bar=document.querySelector('.topbar');
  return {zoom:parseFloat(getComputedStyle(document.body).zoom)||1,
    barRight:get(bar).right,navRight:get(nav).right,viewport:innerWidth,
    brandSize:parseFloat(getComputedStyle(document.querySelector('.topbar .brand__title')).fontSize)};
 });
 expect(v.zoom).toBe(1);
 expect(v.barRight).toBeLessThanOrEqual(v.viewport+2);
 expect(v.navRight).toBeLessThanOrEqual(v.viewport+2);
 expect(v.brandSize).toBeLessThanOrEqual(25);
});
