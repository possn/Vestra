const {test,expect}=require('@playwright/test');
test('iPhone: Market entry cards do not cut text and actual editorial headings are compact',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 await expect(page.locator('#viewMarket')).toBeVisible();
 const evidence=await page.evaluate(()=>{
  const root=document.querySelector('#viewMarket');
  const headings=[...root.querySelectorAll('.market-shell>.market-section:not(:has(.vestra-opportunity-lenses)) .market-section__head h3')].filter(el=>el.getBoundingClientRect().width>0);
  const cards=[...root.querySelectorAll('.market-portfolio-access,.market-scanner-entry')].filter(el=>el.getBoundingClientRect().width>0);
  return {
   viewport:document.documentElement.clientWidth,
   maxHeading:Math.max(0,...headings.map(el=>parseFloat(getComputedStyle(el).fontSize))),
   cards:cards.map(el=>({width:el.getBoundingClientRect().width,screenRight:el.getBoundingClientRect().right,contentRight:Math.max(0,...[...el.querySelectorAll('small,strong')].map(node=>node.getBoundingClientRect().right))})),
   modeWidth:root.querySelector('.market-mode-grid')?.getBoundingClientRect().width
  };
 });
 expect(evidence.maxHeading).toBeLessThanOrEqual(18);
 expect(evidence.cards.length).toBeGreaterThan(0);
 for(const card of evidence.cards){expect(card.screenRight).toBeLessThanOrEqual(evidence.viewport+1);expect(card.contentRight).toBeLessThanOrEqual(card.screenRight+1);}
 expect(evidence.modeWidth).toBeLessThanOrEqual(evidence.viewport);
});
