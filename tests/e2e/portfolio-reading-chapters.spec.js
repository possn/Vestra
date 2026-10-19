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
 const contrast=await portfolio.evaluate(host=>{
  const list=host.querySelector('#itemsList');
  const fixture=document.createElement('div');
  fixture.className='item';
  fixture.innerHTML='<div class="item__l"><div class="item__t">Ativo de teste</div><div class="item__s">Depósitos</div></div><div class="item__v">100 €</div>';
  list.append(fixture);
  const get=selector=>getComputedStyle(host.querySelector(selector));
  const result={
   title:get('.portfolio-hero h2').color,
   heading:get('.portfolio-list-head .card__title').color,
   row:getComputedStyle(fixture).backgroundColor,
   image:getComputedStyle(fixture).backgroundImage,
   name:getComputedStyle(fixture.querySelector('.item__t')).color,
   amount:getComputedStyle(fixture.querySelector('.item__v')).color
  };
  fixture.remove();
  return result;
 });
 expect(contrast.title).toBe('rgb(244, 239, 230)');
 expect(contrast.heading).toBe('rgb(244, 239, 230)');
 expect(contrast.row).toBe('rgb(236, 238, 233)');
 expect(contrast.image).toBe('none');
 expect(contrast.name).toBe('rgb(24, 52, 58)');
 expect(contrast.amount).toBe('rgb(24, 52, 58)');
 const minHeight=await links.evaluateAll(nodes=>nodes.map(x=>x.getBoundingClientRect().height));
 for(const height of minHeight)expect(height).toBeGreaterThanOrEqual(44);
});
