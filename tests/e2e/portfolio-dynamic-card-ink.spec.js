const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');

test('iPhone: dynamic light financial cards use explicit light-surface inks',async({page})=>{
 const source=fs.readFileSync(path.resolve(__dirname,'../../app.js'),'utf8');
 const sources=source.split('function renderPortfolioSourcesCard()',2)[1].split('function renderBrokerImportStatus()',1)[0];
 const milestones=source.split('function renderMilestones()',2)[1].split('function renderMaturityAlerts()',1)[0];
 expect(sources).toContain('background:#eef1ec');
 expect(sources).toContain('color:#19343b');
 expect(sources).toContain('color:#4c6165');
 expect(sources).not.toContain('color:var(--text)');
 expect(sources).not.toContain('color:var(--muted)');
 expect(milestones).toContain('color:#4c6165;margin-top:3px');
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await expect(page.locator('#portfolioSourcesBody')).toHaveCount(1);
 await expect(page.locator('#milestonesContent')).toHaveCount(1);
});
