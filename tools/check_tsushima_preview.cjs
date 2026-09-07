// Local visual QA using the desktop's bundled Playwright and installed Edge.
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.TSUSHIMA_PLAYWRIGHT);
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const page = await browser.newPage();
  const errors=[];
  page.on('pageerror',error=>errors.push(String(error)));
  const file=path.resolve(__dirname,'../timeline/tsushima_togo_turn_qa.html');
  for(const width of [736,360]) {
    await page.setViewportSize({width,height:1100});
    await page.goto(pathToFileURL(file).href);
    const frame=page.frameLocator('iframe');
    await frame.locator('.battle-plot path').first().waitFor();
    const slider=frame.locator('#tsushima-time');
    await slider.fill('600');
    await slider.dispatchEvent('input');
    if(await frame.locator('[data-clock]').textContent()!=='14:10:00')throw Error('Clock failed');
    await frame.locator('[data-ship]').selectOption('12');
    if(!(await frame.locator('[data-detail]').textContent()).includes('スヴォーロフ'))throw Error('Ship selection failed');
    await frame.locator('[data-play]').click();
    await page.waitForTimeout(200);
    await frame.locator('[data-play]').click();
    if(await slider.inputValue()==='600')throw Error('Playback failed');
    // Layout measurements use real browser text bounds, including SVG labels.
    const metrics=await frame.locator('#tsushima-turn-view').evaluate(root=>{
      const width=root.getBoundingClientRect().width;
      const texts=[...root.querySelectorAll('svg text')].map(t=>{const b=t.getBoundingClientRect();return {text:t.textContent,left:b.left,right:b.right};});
      return {width,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,texts};
    });
    if(metrics.scroll>metrics.client+1)throw Error('Horizontal overflow: '+JSON.stringify(metrics));
    for(const colorScheme of ['light','dark']) {
      await page.emulateMedia({colorScheme});
      await page.screenshot({path:path.resolve(__dirname,`../timeline/tsushima_qa_${width}_${colorScheme}.png`),fullPage:true});
    }
    console.log(JSON.stringify({width,metrics}));
  }
  await browser.close();
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Preview: slider, selection, playback, narrow/wide layout passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
