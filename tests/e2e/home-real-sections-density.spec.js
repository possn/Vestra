const {test,expect}=require('@playwright/test');
test('iPhone actual Home barometer/news headings retain compact scale',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.waitForFunction(()=>Boolean(document.querySelector('#vestraIntelligenceHome .vi-news-reading .vi-section-top h3')));
 const sizes=await page.evaluate(()=>{
  const root=document.querySelector('#vestraIntelligenceHome');
  const css=s=>{const el=root.querySelector(s);return el?parseFloat(getComputedStyle(el).fontSize):null;};
  return {news:css('.vi-news-reading .vi-section-top h3'),market:css('.vi-market-reading .vi-section-top h3'),headline:css('.vi-news-reading .vi-editorial-title'),width:document.documentElement.scrollWidth-innerWidth};
 });
 expect(sizes.news).not.toBeNull();expect(sizes.news).toBeLessThanOrEqual(19);
 expect(sizes.market).not.toBeNull();expect(sizes.market).toBeLessThanOrEqual(19);
 expect(sizes.headline).not.toBeNull();expect(sizes.headline).toBeLessThanOrEqual(16);
 expect(sizes.width).toBeLessThanOrEqual(2);
});
