const {test,expect}=require('@playwright/test');
test('iPhone dividend detail: live-looking monthly and top-asset KPI ink is readable',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.evaluate(()=>{
  const view=document.querySelector('#viewDividends');
  view.style.display='block';
  const host=document.querySelector('#divKPIs');
  host.innerHTML='<div class="kpiRow"><div class="kpi"><div class="kpi__k">Este mês</div><div class="kpi__v">€ 123,45</div></div><div class="kpi kpi--net"><div class="kpi__k">Top ativo</div><div class="kpi__v">Empresa · € 450</div></div></div>';
 });
 for(const label of ['Este mês','Top ativo']){
  const card=page.locator('#divKPIs .kpi').filter({hasText:label});
  const value=card.locator('.kpi__v');
  const colors=await value.evaluate(el=>{
   const fg=getComputedStyle(el);const bg=getComputedStyle(el.closest('.kpi'));
   return {foreground:fg.webkitTextFillColor||fg.color,background:bg.backgroundColor,opacity:fg.opacity};
  });
  function rgb(v){const m=v.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);return m?[+m[1],+m[2],+m[3]]:null}
  function luminance(rgb){return rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0)}
  const fg=rgb(colors.foreground),bg=rgb(colors.background);
  expect(fg).not.toBeNull();expect(bg).not.toBeNull();
  const a=luminance(fg),b=luminance(bg);
  expect((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toBeGreaterThanOrEqual(4.5);
  expect(Number(colors.opacity)).toBe(1);
 }
});
