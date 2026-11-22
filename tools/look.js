// My own quick look: open dist/index.html in the bundled Chromium, run one setup expression, save a screenshot.
//   node tools/look.js <name> "<js run in the page>" [width height]
const { chromium } = require('playwright-core');
const path = require('path');
const { pathToFileURL } = require('url');
const EXE = process.env.CHROMIUM_PATH || undefined;
(async () => {
  const [name, js, w, h] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: EXE, args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: +(w || 1440), height: +(h || 900) } });
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(pathToFileURL(path.join(__dirname, '..', 'dist', 'index.html')).href);
  await p.waitForFunction(() => window.gyrus, null, { timeout: 60000 });
  await p.waitForTimeout(1500);
  if (js) await p.evaluate(js);
  await p.waitForTimeout(2200);
  await p.screenshot({ path: path.join(__dirname, '..', 'shots', 'look_' + name + '.png') });
  console.log('saved look_' + name, errs.length ? 'ERRORS ' + errs.join(' | ') : 'no errors');
  await b.close();
})();
