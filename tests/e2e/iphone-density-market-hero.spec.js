const {test,expect}=require('@playwright/test');
test('iPhone compact chrome and Market hero stays inside viewport',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.evaluate(()=>{
  document.querySelector('#viewMarket').removeAttribute('hidden');
  document.querySelector('#viewMarket').style.display='block';
  document.querySelector('#viewDashboard').style.display='none';
 });
 const metrics=await page.evaluate(()=>{
  const h=document.querySelector('#viewMarket .market-hero-simple h2');
  const header=document.querySelector('.topbar');
  const nav=document.querySelector('.bottomnav');
  const input=document.querySelector('#viewMarket .market-search input');
  const rect=h.getBoundingClientRect();
  return {font:parseFloat(getComputedStyle(h).fontSize),rect:{x:rect.x,y:rect.y,right:rect.right,bottom:rect.bottom},header:header.getBoundingClientRect().height,nav:nav.getBoundingClientRect().height,inputFont:input?parseFloat(getComputedStyle(input).fontSize):null,overflow:document.documentElement.scrollWidth-innerWidth};
 });
 expect(metrics.font).toBeLessThanOrEqual(36);
 expect(metrics.rect.x).toBeGreaterThanOrEqual(0);
 expect(metrics.rect.right).toBeLessThanOrEqual(391);
 expect(metrics.header).toBeLessThanOrEqual(85);
 expect(metrics.nav).toBeLessThanOrEqual(105);
 expect(metrics.overflow).toBeLessThanOrEqual(1);
});
test('iPhone Home headline retains compact editorial dimensions',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const headline=page.locator('#vestraIntelligenceHome .vi-home-overview .vi-headline');
 if(await headline.count()){
  const size=await headline.first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize));
  expect(size).toBeLessThanOrEqual(40);
 }
});
