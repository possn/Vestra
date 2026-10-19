const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');

test('iPhone/WebKit: portfolio research does not duplicate the summary strip before Decision Center',async({page})=>{
 const source=fs.readFileSync(path.join(__dirname,'../../market.js'),'utf8');
 const positions=source.slice(source.indexOf("if(tool==='portfolio')"),source.indexOf("if(tool==='theses')"));
 expect(positions).toContain('class="market-portfolio-summary" hidden');
 expect(positions).not.toContain('class="market-portfolio-kpi"');
 expect(positions).toContain('${portfolioIntelligence(rows,researchTotal)}');
 expect(source).toContain('renderPortfolioDecisionCenter(actionRows,total,etfOptimizeRows)');
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await expect(page.locator('#marketSheetContent')).toHaveCount(1);
});
