const {test,expect}=require('@playwright/test');
test('iPhone: Market active indicator is centered in its own touch target',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  const market=page.locator('#navMarket');
  await market.click();
  const geometry=await market.evaluate(button=>{
    const icon=button.querySelector('.navico');
    const nav=button.closest('.bottomnav');
    const b=button.getBoundingClientRect(),i=icon.getBoundingClientRect(),n=nav.getBoundingClientRect();
    const style=getComputedStyle(icon);
    return {delta:Math.abs((b.left+b.right-i.left-i.right)/2),
      navLeft:n.left,navRight:n.right,viewport:innerWidth,
      transform:style.transform,touchHeight:b.height,shadow:style.boxShadow};
  });
  expect(geometry.delta).toBeLessThanOrEqual(1);
  expect(geometry.navLeft).toBeGreaterThanOrEqual(-1);
  expect(geometry.navRight).toBeLessThanOrEqual(geometry.viewport+1);
  expect(geometry.transform).toBe('none');
  expect(geometry.touchHeight).toBeGreaterThanOrEqual(44);
  expect(geometry.shadow).toBe('none');
});
