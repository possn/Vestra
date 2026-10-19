const {test,expect}=require('@playwright/test');
test('FIRE editorial order: conclusion, evidence, assumptions, details',async({page})=>{
 await page.goto('/index.html');
 const structure=await page.locator('#analysisPanelTab_fire').evaluate(p=>{
  const children=[...p.children];return {
   results:children.findIndex(e=>e.querySelector('#fireResults')),
   status:children.findIndex(e=>e.id==='fireStatusCard'),
   assumptions:children.findIndex(e=>e.querySelector('#btnToggleFireInputs')),
   chart:children.findIndex(e=>e.querySelector('#fireChart')),
   count:p.querySelectorAll('#fireResults,#fireCap,#fireInputsBody,#fireChart').length
  };
 });
 expect(structure.count).toBe(4);
 expect(structure.results).toBeLessThan(structure.status);
 expect(structure.status).toBeLessThan(structure.assumptions);
 expect(structure.assumptions).toBeLessThan(structure.chart);
});
