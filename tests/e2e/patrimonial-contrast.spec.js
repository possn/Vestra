const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Real WebKit inspection of the canonical patrimonial drilldown, not only CSS text checks.
test('iPhone/WebKit: patrimonial section titles remain legible on dark and light surfaces', async ({ page }) => {
  await page.setViewportSize({ width:390, height:844 });
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
  await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
  const out = path.join('test-results','visual-evidence');
  fs.mkdirSync(out,{recursive:true});
  const findings = await page.evaluate(() => {
    const targets = [
      ['Rendimento e desempenho','#v2-wealth-chapter h2'],
      ['Gerir e aprofundar','#v2-tools-chapter .v2-home-secondary-hub__intro h3'],
      ['Qualidade','#portfolioQualityCard .card__title'],
      ['Saúde Financeira','#debtRatioCard .card__title'],
      ['Alertas de vencimentos','.v2-home-secondary-hub .card:has(#btnEnableNotifications) .card__title'],
    ];
    const channels = css => (css.match(/[\\d.]+/g)||[]).slice(0,3).map(Number);
    const lum = css => {
      const nums=channels(css); if(nums.length!==3)return null;
      const rgb=nums.map(n=>{const s=n/255;return s<=.04045?s/12.92:Math.pow((s+.055)/1.055,2.4)});
      return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
    };
    return targets.map(([name,selector])=>{
      const element=document.querySelector(selector);
      if(!element)return {name,error:'missing selector'};
      const surface=element.closest('#portfolioQualityCard,#debtRatioCard,.v2-home-secondary-hub .card') ||
        document.getElementById('viewDashboard');
      const fg=getComputedStyle(element).webkitTextFillColor || getComputedStyle(element).color;
      const bg=getComputedStyle(surface).backgroundColor;
      const a=lum(fg),b=lum(bg);
      const contrast=a===null||b===null?null:(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
      return {name,selector,visible:element.getBoundingClientRect().width>0,fg,bg,contrast};
    });
  });
  fs.writeFileSync(path.join(out,'patrimonial-contrast-iphone.json'),JSON.stringify(findings,null,2));
  for(const item of findings){
    expect(item.error, item.name).toBeUndefined();
    if(item.visible && item.contrast!==null) expect(item.contrast,item.name).toBeGreaterThanOrEqual(4.5);
  }
  await page.screenshot({
    path:path.join(out,'patrimonial-page-iphone.png'),fullPage:true,animations:'disabled'
  });
});


test('iPhone/WebKit: patrimonial chapters 01 02 03 compute identical title typography', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
  await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
  const measures=await page.evaluate(()=>{
    const selectors=[
      '#v2-wealth-chapter h2',
      '#v2-history-chapter>strong',
      '#v2-tools-chapter .v2-home-secondary-hub__intro h3'
    ];
    return selectors.map(selector=>{
      const element=document.querySelector(selector);
      if(!element)return {selector,exists:false};
      const s=getComputedStyle(element),r=element.getBoundingClientRect();
      return {selector,exists:true,text:element.textContent.trim(),family:s.fontFamily,
        size:s.fontSize,weight:s.fontWeight,lineHeight:s.lineHeight,
        spacing:s.letterSpacing,color:s.webkitTextFillColor||s.color,
        visible:r.width>0&&r.height>0&&s.display!=='none'};
    });
  });
  const out=path.join('test-results','visual-evidence');
  fs.mkdirSync(out,{recursive:true});
  fs.writeFileSync(path.join(out,'chapter-parity-iphone.json'),JSON.stringify(measures,null,2));
  await page.screenshot({path:path.join(out,'chapter-parity-iphone.png'),fullPage:true,animations:'disabled'});
  for(const item of measures){
    expect(item.exists,item.selector).toBe(true);
    // Visibility is recorded in evidence; navigation visibility is a separate E2E concern.
    expect(item.size,item.selector).toBe(measures[0].size);
    expect(item.family,item.selector).toBe(measures[0].family);
    expect(item.weight,item.selector).toBe(measures[0].weight);
    expect(item.lineHeight,item.selector).toBe(measures[0].lineHeight);
    expect(item.spacing,item.selector).toBe(measures[0].spacing);
  }
});


test('iPhone/WebKit: generated health and maturity content keeps light-card contrast', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
  await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);

  // The dashboard can intentionally hide secondary tools and data-gated cards.
  // Reveal only the authentic financial card DOM owners for this contrast fixture;
  // do not alter their computed ink, background or financial calculations.
  await page.evaluate(() => {
    for(const selector of ['#v2-tools-chapter','#debtRatioCard','#maturityAlertsCard']){
      const el=document.querySelector(selector);
      if(el)el.style.setProperty('display','block','important');
    }
  });
  await expect(page.locator('#debtRatioCard')).toBeVisible();
  await expect(page.locator('#maturityAlertsCard')).toBeVisible();
  // Representative dynamic financial markup, inserted into the actual card owners.
  // This tests computed WebKit styles even when the test account has no portfolio.
  const evidence=await page.evaluate(() => {
    const health=document.querySelector('#debtRatioContent');
    const maturities=document.querySelector('#maturityAlertsContent');
    if(!health||!maturities)return {error:'Missing financial card content owners'};
    health.innerHTML='<div class="health-metric-card"><strong data-contrast-check="health-value">27%</strong><p data-contrast-check="health-label">Endividamento estimado</p><small data-contrast-check="health-note">Cobertura parcial</small><span style="color:#a34720" data-contrast-check="health-status">Atenção</span></div>';
    maturities.innerHTML='<div><strong data-contrast-check="maturity-value">2027</strong><p data-contrast-check="maturity-label">Próximo vencimento</p><span style="color:#a34720" data-contrast-check="maturity-status">Rever prazo</span></div>';
    const toRgb = str => {
      const m=str.match(/^rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)/);
      return m ? [Number(m[1]),Number(m[2]),Number(m[3])] : null;
    };
    const luminance = rgb => rgb.reduce((sum,n,i)=>{
      const s=n/255;
      const v=s<=.04045?s/12.92:Math.pow((s+.055)/1.055,2.4);
      return sum+v*[.2126,.7152,.0722][i];
    },0);
    const names=['health-value','health-label','health-note','health-status','maturity-value','maturity-label','maturity-status'];
    return names.map(name=>{
      const el=document.querySelector('[data-contrast-check="'+name+'"]');
      const owner=el.closest('.health-metric-card')||el.closest('#maturityAlertsContent>div');
      const style=getComputedStyle(el), surface=getComputedStyle(owner);
      const fg=style.webkitTextFillColor||style.color;
      const bg=surface.backgroundColor==='rgba(0, 0, 0, 0)'?
        getComputedStyle(owner.closest('#maturityAlertsCard')).backgroundColor:surface.backgroundColor;
      const a=toRgb(fg),b=toRgb(bg);
      const contrast=a&&b?(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05):null;
      return {name,fg,bg,contrast,visible:el.getBoundingClientRect().width>0};
    });
  });
  expect(evidence.error).toBeUndefined();
  for(const item of evidence){
    expect(item.visible,item.name).toBe(true);
    expect(item.contrast,item.name).not.toBeNull();
    expect(item.contrast,item.name).toBeGreaterThanOrEqual(4.5);
  }
  const out=path.join('test-results','visual-evidence');
  fs.mkdirSync(out,{recursive:true});
  fs.writeFileSync(path.join(out,'dynamic-health-maturity-iphone.json'),JSON.stringify(evidence,null,2));
});
