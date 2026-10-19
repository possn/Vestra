const {test,expect}=require('@playwright/test');
test('iPhone loads canonical scale after all legacy stylesheets',async({page})=>{
 await page.goto('/index.html');
 const order=await page.locator('link[rel="stylesheet"]').evaluateAll(links=>links.map(l=>l.getAttribute('href')));
 expect(order.at(-1)).toMatch(/^vestra-iphone-canonical-scale\.css\?v=/);
});
test('iPhone real Home, Portfolio and Market typography stays compact',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const values=await page.evaluate(()=>{
  const size=s=>{const el=document.querySelector(s);return el?parseFloat(getComputedStyle(el).fontSize):null};
  return {home:size('#vestraIntelligenceHome .vi-section-top h3'),
   portfolio:size('#viewAssets .view-intro h2'),
   market:size('#viewMarket .market-hero-simple h2'),
   overflow:document.documentElement.scrollWidth-innerWidth};
 });
 expect(values.home).not.toBeNull();expect(values.home).toBeLessThanOrEqual(19);
 expect(values.portfolio).not.toBeNull();expect(values.portfolio).toBeLessThanOrEqual(32);
 expect(values.market).not.toBeNull();expect(values.market).toBeLessThanOrEqual(36);
 expect(values.overflow).toBeLessThanOrEqual(2);
});
