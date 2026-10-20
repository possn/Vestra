const {test,expect}=require('@playwright/test');
test('rebalancing conclusion precedes advanced performance evidence',async({page})=>{
 await page.goto('/index.html');
 const sections=await page.locator('#analysisPanelTab_performance').evaluate(panel=>{
  const children=[...panel.children];
  const reb=children.findIndex(el=>el.querySelector('#rebalancingContent'));
  const evidence=children.findIndex(el=>el.querySelector('#benchmarkContent'));
  return {reb,evidence,rebalancing:panel.querySelectorAll('#rebalancingContent').length,benchmark:panel.querySelectorAll('#benchmarkContent').length};
 });
 expect(sections.reb).toBe(0);
 expect(sections.evidence).toBe(1);
 expect(sections.rebalancing).toBe(1);
 expect(sections.benchmark).toBe(1);
});
