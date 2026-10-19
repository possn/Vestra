const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: portfolio has direct chapter navigation without duplicated financial hosts',async ({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navAssets').click();
 const portfolio=page.locator('#viewAssets');
 await expect(portfolio).toBeVisible();
 const nav=portfolio.locator('.portfolio-chapter-nav');
 await expect(nav).toBeVisible();
 const targets=['portfolioGlance','portfolioPositionsChapter','portfolioToolsStrip'];
 const links=nav.locator('a');
 await expect(links).toHaveCount(3);
 for(let i=0;i<targets.length;i++){
  await expect(links.nth(i)).toHaveAttribute('href','#'+targets[i]);
  await expect(portfolio.locator('#'+targets[i])).toHaveCount(1);
 }
 for(const id of ['portfolioTotalValue','portfolioPositionCount','itemsList','btnPortfolioFilters']){
  await expect(portfolio.locator('#'+id)).toHaveCount(1);
 }
 const editorial=await portfolio.evaluate(host=>{
  const summary=host.querySelector('#portfolioGlance');
  const positions=host.querySelector('#portfolioPositionsChapter');
  const heading=host.querySelector('.portfolio-list-head .card__title');
  return {
   summaryLayout:getComputedStyle(summary).display,
   positionShadow:getComputedStyle(positions).boxShadow,
   headingFamily:getComputedStyle(heading).fontFamily
  };
 });
 expect(editorial.summaryLayout).toBe('grid');
 expect(editorial.positionShadow).toBe('none');
 expect(editorial.headingFamily).toContain('Georgia');
 const minHeight=await links.evaluateAll(nodes=>nodes.map(x=>x.getBoundingClientRect().height));
 for(const height of minHeight)expect(height).toBeGreaterThanOrEqual(44);
});
