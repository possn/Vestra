const {test,expect}=require('@playwright/test');

test('iPhone: compact content and navigation across all seven active views',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const routes=[
  ['dashboard','#navDashboard'],['assets','#navAssets'],
  ['market','#navMarket'],['cashflow','#navCashflow'],
  ['dividends',null],['analysis',null],['settings','#navSettings']
 ];
 for(const [route,nav] of routes){
  if(nav) await page.locator(nav).click();
  else await page.evaluate(name=>window.setView(name),route);
  const view=page.locator('[data-view="'+route+'"].view').first();
  await expect(view,route+' must be active').toBeVisible();
  const result=await page.evaluate(id=>{
   const root=document.documentElement;
   const section=document.querySelector('.view[data-view="'+id+'"]');
   const r=section.getBoundingClientRect();
   const content=[...section.querySelectorAll('.card')].filter(el=>{
    const rect=el.getBoundingClientRect();
    return rect.width>0&&rect.height>0&&getComputedStyle(el).visibility!=='hidden';
   }).slice(0,5).map(el=>({padding:parseFloat(getComputedStyle(el).paddingLeft),right:el.getBoundingClientRect().right}));
   const nav=document.querySelector('.bottomnav').getBoundingClientRect();
   const top=document.querySelector('.topbar').getBoundingClientRect();
   return {
    viewport:root.clientWidth,scrollWidth:root.scrollWidth,
    width:r.width,right:r.right,content,
    navRight:nav.right,topRight:top.right,
    zoom:parseFloat(getComputedStyle(document.body).zoom)||1
   };
  },route);
  expect(result.viewport,route+' viewport').toBeLessThanOrEqual(390);
  expect(result.scrollWidth,route+' horizontal document overflow').toBeLessThanOrEqual(result.viewport+2);
  expect(result.width,route+' section width').toBeLessThanOrEqual(result.viewport+1);
  expect(result.right,route+' section right edge').toBeLessThanOrEqual(result.viewport+2);
  expect(result.navRight,route+' bottom nav').toBeLessThanOrEqual(result.viewport+2);
  expect(result.topRight,route+' topbar').toBeLessThanOrEqual(result.viewport+2);
  expect(result.zoom,route+' must not zoom').toBe(1);
  for(const card of result.content){
   expect(card.padding,route+' card padding').toBeLessThanOrEqual(13);
   expect(card.right,route+' card clipping').toBeLessThanOrEqual(result.viewport+2);
  }
 }
});

// Regression evidenced by real installed-iPhone captures: readable dark intro
// text, full-width Market rail and no horizontal bleed of action surfaces.
test('iPhone: readable native headings and constrained Market rail',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 for(const [view,selector] of [['assets','#viewAssets .portfolio-hero h2'],['cashflow','#viewCashflow .flow-hero h2']]){
  await page.evaluate(v=>setView(v),view);
  const ink=await page.locator(selector).evaluate(el=>{
   const c=getComputedStyle(el).color;
   const canvas=document.createElement('canvas');
   canvas.width=canvas.height=1;
   const ctx=canvas.getContext('2d');
   ctx.fillStyle=c;
   ctx.fillRect(0,0,1,1);
   const rgb=Array.from(ctx.getImageData(0,0,1,1).data).slice(0,3);
   return {rgb,opacity:Number(getComputedStyle(el).opacity)};
  });
  expect(ink.rgb.every(n=>n>=180),view+' heading must be legible on dark background').toBe(true);
  expect(ink.opacity,view+' heading opacity').toBeGreaterThanOrEqual(.99);
 }
 await page.locator('#navMarket').click();
 const rail=page.locator('#viewMarket .market-mode-grid').first();
 await expect(rail).toBeVisible();
 const bounds=await rail.evaluate(el=>{
  const r=el.getBoundingClientRect();
  const p=el.parentElement.getBoundingClientRect();
  return {left:r.left,right:r.right,parentRight:p.right,viewport:document.documentElement.clientWidth};
 });
 expect(bounds.left).toBeGreaterThanOrEqual(0);
 expect(bounds.right).toBeLessThanOrEqual(Math.min(bounds.parentRight,bounds.viewport)+2);
});

// Physical iPhone audit: a single action to record a movement in Cashflow.
test('iPhone: Cashflow has one visible movement action', async ({page}) => {
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.waitForFunction(() => window.__vestraAppHydrated === true);
 await page.evaluate(() => setView('cashflow'));
 await expect(page.locator('#viewCashflow #btnAddTx')).toBeVisible();
 await expect(page.locator('#viewCashflow button').filter({hasText:'+ Movimento'})).toHaveCount(1);
});

// Editorial density: important Market action copy should remain legible on a 390px iPhone.
test('iPhone: Market portfolio action has concise uncropped context', async ({page}) => {
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 const action=page.locator('#viewMarket .market-portfolio-access');
 await expect(action).toBeVisible();
 const copy=action.locator('small');
 await expect(copy).toHaveText('Convicção · riscos · alternativas');
 const bounds=await copy.evaluate(el=>{
  const r=el.getBoundingClientRect();
  const p=el.closest('.market-portfolio-access').getBoundingClientRect();
  return {left:r.left,right:r.right,parentRight:p.right,viewport:document.documentElement.clientWidth};
 });
 expect(bounds.left).toBeGreaterThanOrEqual(0);
 expect(bounds.right).toBeLessThanOrEqual(Math.min(bounds.parentRight,bounds.viewport)+2);
});

test('iPhone: portfolio summary uses editorial density without clipping values',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navAssets').click();
 const summary=page.locator('#viewAssets #portfolioGlance');
 await expect(summary).toBeVisible();
 const geometry=await summary.evaluate(el=>{
  const style=getComputedStyle(el);
  const main=el.querySelector('.portfolio-glance__main');
  const stats=[...el.querySelectorAll('.portfolio-glance__stat')];
  const bounds=el.getBoundingClientRect();
  return {radius:parseFloat(style.borderTopLeftRadius),padding:parseFloat(style.paddingTop),
   mainHeight:main.getBoundingClientRect().height,
   statsHeights:stats.map(x=>x.getBoundingClientRect().height),
   right:bounds.right,viewport:document.documentElement.clientWidth};
 });
 expect(geometry.radius).toBeLessThanOrEqual(19);
 expect(geometry.padding).toBeLessThanOrEqual(10);
 expect(geometry.mainHeight).toBeLessThanOrEqual(105);
 expect(geometry.statsHeights.every(h=>h<=80)).toBe(true);
 expect(geometry.right).toBeLessThanOrEqual(geometry.viewport+2);
});

test('iPhone: Market horizontal mode rail is scrollable without expanding page',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 const rail=page.locator('#viewMarket .market-mode-grid');
 await expect(rail).toBeVisible();
 const geometry=await rail.evaluate(el=>{
  const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
  return {left:r.left,right:r.right,viewport:document.documentElement.clientWidth,
   overflow:cs.overflowX,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth};
 });
 expect(geometry.left).toBeGreaterThanOrEqual(0);
 expect(geometry.right).toBeLessThanOrEqual(geometry.viewport+2);
 expect(geometry.overflow).toBe('auto');
 expect(geometry.scrollWidth).toBeGreaterThan(geometry.clientWidth);
 const last=rail.locator('.market-mode').last();
 await last.scrollIntoViewIfNeeded();
 await expect(last).toBeInViewport();
});

test('iPhone: Ideas market content stays inside viewport and has readable title ink',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 await page.locator('[data-market-mode="discover"]').click();
 const report=await page.locator('#viewMarket #marketPrimary').evaluate(root=>{
  const styles=getComputedStyle(root);
  const bad=[...root.querySelectorAll('section,article,.market-row,.market-sector-grid,.ux453-opp')].filter(el=>{
   const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
   return r.width>0&&r.height>0&&cs.display!=='none'&&
    (r.right>document.documentElement.clientWidth+3 || r.left< -3) &&
    cs.position!=='absolute'&&cs.position!=='fixed'&&
    !el.closest('.market-chipbar');
  }).slice(0,10).map(el=>({tag:el.tagName,className:String(el.className).slice(0,90)}));
  const heads=[...root.querySelectorAll('.market-section__head h3')].map(el=>({
   size:parseFloat(getComputedStyle(el).fontSize),ink:getComputedStyle(el).color
  }));
  return {width:root.getBoundingClientRect().width,viewport:document.documentElement.clientWidth,
   bad,heads,overflow:styles.overflowX};
 });
 expect(report.width).toBeLessThanOrEqual(report.viewport);
 expect(report.bad).toEqual([]);
 for(const head of report.heads){
  expect(head.size).toBeLessThanOrEqual(19);
  expect(head.ink).not.toBe('rgb(255, 255, 255)');
 }
});

test('iPhone: real Ideas opportunity score is a compact badge, not a tall empty rail',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 await page.locator('[data-market-mode="discover"]').click();
 const card=page.locator('#viewMarket .ux453-opp').first();
 await expect(card).toBeVisible({timeout:15000});
 const sizes=await card.evaluate(el=>{
  const outer=el.getBoundingClientRect();
  const score=el.querySelector('.ux453-entry')?.getBoundingClientRect();
  const detail=el.querySelector('.ux453-detail-grid')?.getBoundingClientRect();
  return {right:outer.right,viewport:document.documentElement.clientWidth,
   scoreHeight:score?.height,scoreWidth:score?.width,
   cardHeight:outer.height,detailWidth:detail?.width};
 });
 expect(sizes.right).toBeLessThanOrEqual(sizes.viewport+2);
 expect(sizes.scoreWidth).toBeLessThanOrEqual(66);
 expect(sizes.scoreHeight).toBeLessThanOrEqual(100);
 expect(sizes.cardHeight).toBeLessThan(460);
 expect(sizes.detailWidth).toBeGreaterThan(100);
});
