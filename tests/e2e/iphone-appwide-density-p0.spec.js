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
