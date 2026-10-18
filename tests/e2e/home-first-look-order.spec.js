const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: first look is wealth, barometer, news, horizontal agenda, portfolio', async ({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const home=page.locator('#vestraIntelligenceHome');
 await expect(home).toBeVisible({timeout:20000});
 const report=await home.evaluate(host=>{
  const names=['.vi-wealth','.vi-market-reading','.vi-news-reading','.vi-events-reading','.vi-priorities','.vi-risk-reading'];
  const sections=names.map(selector=>host.querySelector(selector));
  const rail=host.querySelector('.vi-events-reading .vi-editorial-rail');
  const style=getComputedStyle(rail);
  return {
   present:sections.map(Boolean),
   order:sections.map(el=>el?.getBoundingClientRect().top),
   strip:!!host.querySelector('.vi-signal-strip'),
   overflowX:style.overflowX, snap:style.scrollSnapType,
   railWidth:rail.clientWidth,
   tileWidth:rail.querySelector('.vi-editorial-tile')?.getBoundingClientRect().width??0
  };
 });
 expect(report.present).toEqual([true,true,true,true,true,true]);
 for(let i=1;i<report.order.length;i++)
  expect(report.order[i], 'reading order '+i).toBeGreaterThan(report.order[i-1]);
 expect(report.strip).toBe(false);
 expect(report.overflowX).toBe('auto');
 expect(report.snap).toContain('x');
 await expect(home.locator('.vi-priorities .vi-action')).toHaveCount(3);
});
