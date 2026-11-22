// Recall, endless: 3 clean names, 1 name with two typos fixed by backspace, 1 wrong answer, then Review.
const { chromium } = require('playwright-core');
const path = require('path');
const { pathToFileURL } = require('url');
const EXE = process.env.CHROMIUM_PATH || undefined;
(async () => {
  const b = await chromium.launch({ executablePath: EXE, args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', (e) => errs.push(e.message));
  await p.goto(pathToFileURL(path.join(__dirname, '..', 'dist', 'index.html')).href);
  await p.waitForFunction(() => window.gyrus, null, { timeout: 60000 });
  await p.waitForTimeout(1500);
  await p.evaluate(() => { gyrus.setDeck('lobes'); gyrus.setSub('recall'); });
  const name = () => p.evaluate(() => gyrus.T && !gyrus.T.done ? gyrus.T.r.name : '');
  const stats = () => p.evaluate(() => document.querySelector('#stats').innerText.replace(/\s+/g, ' '));
  for (let i = 0; i < 3; i++) { await p.waitForTimeout(700); await p.focus('#typer'); await p.keyboard.type(await name(), { delay: 60 }); await p.waitForTimeout(700); }
  console.log('after 3 clean:', await stats());
  await p.waitForTimeout(500); const n = await name();
  await p.keyboard.type(n.slice(0, 3), { delay: 60 }); await p.keyboard.type('qz', { delay: 60 }); await p.keyboard.press('Backspace'); await p.keyboard.press('Backspace');
  await p.keyboard.type(n.slice(3), { delay: 60 }); await p.waitForTimeout(800);
  console.log('after 2 typos fixed:', await stats());
  await p.waitForTimeout(500);
  await p.keyboard.type('pons', { delay: 60 }); await p.keyboard.press('Enter'); await p.waitForTimeout(800);
  const n2 = await p.evaluate(() => gyrus.T.r.name); await p.keyboard.type(n2, { delay: 60 }); await p.waitForTimeout(900);
  console.log('after a wrong answer:', await stats());
  await p.click('[data-review]'); await p.waitForTimeout(1200);
  await p.screenshot({ path: path.join(__dirname, '..', 'shots', 'acc_review.png') });
  console.log('review:', (await p.evaluate(() => document.querySelector('#word').innerText)).replace(/\s+/g, ' ').slice(0, 300));
  await p.keyboard.press('Enter'); await p.waitForTimeout(900);
  console.log('after Enter (keep going):', await stats(), '| target', await name());
  console.log(errs.length ? 'ERRORS ' + errs.join(' | ') : 'no errors');
  await b.close();
})();
