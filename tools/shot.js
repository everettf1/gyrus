// Screenshot pass for dist/index.html using Playwright's bundled Chromium (never Google Chrome).
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright-core');
const EXE = process.env.CHROMIUM_PATH || undefined;
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'shots');
fs.mkdirSync(OUT, { recursive: true });
const only = process.argv.slice(2);

(async () => {
  const browser = await chromium.launch({ executablePath: EXE, args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const errors = [];
  async function open(w, h) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.on('console', m => { if (m.type() === 'error') errors.push(w + ': ' + m.text()); });
    page.on('pageerror', e => errors.push(w + ' pageerror: ' + e.message));
    await page.goto('file:///' + path.join(ROOT, 'dist', 'index.html').replace(/\\/g, '/'));
    await page.waitForFunction(() => window.gyrus, null, { timeout: 60000 });
    await page.waitForTimeout(2500);
    return page;
  }
  const shot = async (page, name) => { await page.waitForTimeout(1600); await page.screenshot({ path: path.join(OUT, name + '.png') }); console.log('saved', name); };
  const want = n => !only.length || only.includes(n);

  const p = await open(1440, 900);
  if (want('lateral')) await shot(p, 'lateral');
  if (want('explore')) { await p.evaluate(() => window.gyrus.select('prefrontal_cortex')); await shot(p, 'explore_pfc'); }
  if (want('medial')) { await p.evaluate(() => { window.gyrus.setDeck('areas'); window.gyrus.select('anterior_cingulate_cortex'); }); await shot(p, 'medial_acc'); }
  if (want('superior')) { await p.evaluate(() => { window.gyrus.select('primary_motor_cortex'); window.gyrus.setView('superior'); }); await shot(p, 'superior'); }
  if (want('deep')) { await p.evaluate(() => { window.gyrus.setDeck('deep'); window.gyrus.select('hippocampus'); }); await shot(p, 'deep_hippocampus'); }
  if (want('thalamus')) { await p.evaluate(() => { window.gyrus.setDeck('thalamus'); window.gyrus.select('pulvinar'); }); await shot(p, 'thalamus'); }
  if (want('slice')) { await p.evaluate(() => { window.gyrus.setMode('explore'); window.gyrus.setDeck('areas'); window.gyrus.set('axis', 'sagittal'); window.gyrus.set('slice', .5); window.gyrus.setView('lateral'); }); await shot(p, 'slice'); await p.evaluate(() => window.gyrus.set('slice', 0)); }
  if (want('type')) {
    await p.evaluate(() => { window.gyrus.setDeck('lobes'); window.gyrus.setMode('type'); });
    await p.waitForTimeout(1200);
    const name = await p.evaluate(() => window.gyrus.T.r.name);
    await p.keyboard.type(name.slice(0, Math.ceil(name.length / 2)), { delay: 30 });
    await shot(p, 'type_midword');
  }
  if (want('find')) { await p.evaluate(() => window.gyrus.setMode('find')); await shot(p, 'find'); }
  if (want('quiz')) { await p.evaluate(() => { window.gyrus.setDeck('areas'); window.gyrus.setMode('quiz'); }); await shot(p, 'quiz'); }
  if (want('learn')) { await p.evaluate(() => { window.gyrus.setMode('learn'); }); await p.keyboard.press('Space'); await p.keyboard.press('Space'); await shot(p, 'learn'); }
  await p.context().close();

  if (want('phone')) {
    const m = await open(400, 860);
    await m.evaluate(() => window.gyrus.select('prefrontal_cortex'));
    await shot(m, 'phone');
    const sw = await m.evaluate(() => document.documentElement.scrollWidth);
    console.log('phone scrollWidth', sw);
    await m.screenshot({ path: path.join(OUT, 'phone_full.png'), fullPage: true });
    await m.context().close();
  }
  console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no console errors');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
