const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    fs.mkdirSync('../test-results', { recursive: true });
    await page.goto('http://127.0.0.1:8014/');
    await page.locator('input[type=file]').setInputFiles(path.join(__dirname, 'synthetic-shapes.png'));
    if (await page.locator('[name=allow_external_analysis]').isChecked()) throw Error('External consent must default off');
    await page.locator('button[type=submit]').click();
    await page.waitForURL('**/result/*/');
    await page.getByText('Uncalibrated heuristic scores.', { exact: true }).waitFor();
    await page.getByText('External model analysis was not requested.', { exact: true }).waitFor();
    await page.waitForFunction(() => getComputedStyle(document.body).backgroundColor === 'rgb(2, 6, 23)');
    await page.locator('img').evaluate(im => im.decode());
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw Error('Horizontal overflow at ' + width);
      await page.screenshot({ path: `../test-results/result-${width}.png`, fullPage: true });
    }
    const stranger = await browser.newContext();
    if ((await stranger.request.get(page.url())).status() !== 404) throw Error('Private result exposed');
    if (errors.length) throw Error(JSON.stringify(errors));
    fs.writeFileSync('../test-results/browser.json', JSON.stringify({ browser: browser.version(), checks: ['local upload', 'external consent off', 'score disclaimer', 'external analysis disabled', 'stranger denied', 'three responsive widths', 'no page errors'], date: new Date().toISOString() }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
