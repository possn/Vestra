const {test,expect}=require('@playwright/test');

test('iPhone: Dividendos and Análise return actions retain readable light ink',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  for(const id of ['viewDividends','viewAnalysis']){
    const button=page.locator('#'+id+' > .vestra-light-return');
    await expect(button).toHaveCount(1);
    await page.evaluate(id=>{
      document.querySelectorAll('.view').forEach(el=>el.style.display='none');
      document.getElementById(id).style.display='block';
    },id);
    const s=await button.evaluate(el=>{
      const c=getComputedStyle(el);
      return {color:c.color,webkit:c.webkitTextFillColor,bg:c.backgroundColor,opacity:c.opacity};
    });
    const rgb=str=>{const m=str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);return m?[+m[1],+m[2],+m[3]]:null;};
    const lum=a=>a.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((v,n,i)=>v+n*[.2126,.7152,.0722][i],0);
    const foreground=rgb(s.webkit)||rgb(s.color),background=rgb(s.bg);
    expect(foreground).not.toBeNull();expect(background).not.toBeNull();
    const a=lum(foreground),b=lum(background),contrast=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    expect(contrast).toBeGreaterThanOrEqual(4.5);
    expect(Number(s.opacity)).toBe(1);
  }
});
