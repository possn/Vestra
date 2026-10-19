const {test,expect}=require('@playwright/test');
test('iPhone light financial cards and historical rotation use readable text',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const result=await page.evaluate(()=>{
  const cards=['portfolioSourcesCard','goalCard','milestonesCard','portfolioQualityCard','irsEstCard','maturityAlertsCard'];
  const root=document.querySelector('#viewDashboard');
  const nodes=cards.map(id=>{
   const element=root.querySelector('#'+id);
   const title=element.querySelector('.card__title');
   const subtitle=element.querySelector('.card__muted');
   return {id,title:getComputedStyle(title).color,subtitle:getComputedStyle(subtitle).color};
  });
  const el=document.createElement('p');
  el.className='market-rotation-freshness-warning';
  const parent=document.createElement('div');
  parent.className='market-rotation';
  parent.append(el);
  document.querySelector('#viewMarket').append(parent);
  const stale=getComputedStyle(el).color;
  parent.remove();
  return {nodes,stale};
 });
 for(const c of result.nodes){
  expect(c.title,c.id).toBe(c.id==='irsEstCard'?'rgb(117, 69, 21)':'rgb(25, 52, 59)');
  expect(c.subtitle,c.id).toBe('rgb(76, 97, 101)');
 }
 expect(result.stale).toBe('rgb(115, 75, 36)');
});
