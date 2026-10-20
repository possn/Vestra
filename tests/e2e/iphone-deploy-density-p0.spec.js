const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
test('PWA requests new compact generation and forbids cross-version CSS fallback',async({page})=>{
 await page.goto('/index.html');
 const links=await page.locator('link[rel="stylesheet"]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
 expect(links).toContain('vestra-iphone-canonical-scale.css?v=20261020-premium-rhythm');
 const sw=fs.readFileSync('sw.js','utf8');
 expect(sw).toContain('vestra-cache-v242');
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
 for(const [key,limit] of Object.entries({headline:30,chapter:17,portfolio:29,total:34,market:32})){
  expect(values[key],key).not.toBeNull();
  expect(values[key],key).toBeLessThanOrEqual(limit);
 }
});
