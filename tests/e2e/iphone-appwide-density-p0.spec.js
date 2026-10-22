const {test,expect}=require('@playwright/test');
test('iPhone: app-wide compact content contract across every native view',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const measures=await page.evaluate(()=>{
  const out=[];
  for(const id of ['viewDashboard','viewAssets','viewCashflow','viewMarket','viewDividends','viewAnalysis','viewSettings']){
   const view=document.getElementById(id);
   const style=getComputedStyle(view);
   const cards=[...view.querySelectorAll('.card')].slice(0,3).map(el=>({padding:parseFloat(getComputedStyle(el).paddingLeft),radius:parseFloat(getComputedStyle(el).borderTopLeftRadius)}));
   out.push({id,exists:!!view,cssWidth:style.maxWidth,cards});
  }
  return {viewport:document.documentElement.clientWidth,layoutViewport:innerWidth,views:out};
 });
 expect(measures.viewport).toBeLessThanOrEqual(390);
 for(const item of measures.views){expect(item.exists,item.id).toBe(true);for(const card of item.cards){expect(card.padding,item.id).toBeLessThanOrEqual(13);}}
 const selectors=['#viewMarket','#viewAssets','#viewCashflow','#viewDividends','#viewAnalysis','#viewSettings'];
 for(const selector of selectors){const metrics=await page.locator(selector).evaluate(el=>({width:el.getBoundingClientRect().width,root:document.documentElement.clientWidth}));expect(metrics.width,selector).toBeLessThanOrEqual(metrics.root+1);}
});
