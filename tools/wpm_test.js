// Type region names with real key events at a fixed pace and compare the page's wpm with the true rate.
//   node tools/wpm_test.js <msPerKey> [items]
const { chromium } = require('playwright-core');
const path = require('path');
const { pathToFileURL } = require('url');
const EXE = process.env.CHROMIUM_PATH || undefined;
(async () => {
  const D = +(process.argv[2] || 100), N = +(process.argv[3] || 12);
  const b = await chromium.launch({ executablePath: EXE, args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(pathToFileURL(path.join(__dirname, '..', 'dist', 'index.html')).href);
  await p.waitForFunction(() => window.gyrus, null, { timeout: 60000 });
  await p.waitForTimeout(1500);
  await p.evaluate((d) => { gyrus.setDeck(d); gyrus.setSub('recall'); }, process.env.DECK || 'gyri');
  await p.waitForTimeout(800);
  let chars = 0, keyMs = 0;
  for (let i = 0; i < N; i++) {
    await p.waitForTimeout(700);
    const name = await p.evaluate(() => gyrus.T && !gyrus.T.done ? gyrus.T.r.name : '');
    if (!name) continue;
    await p.focus('#typer');
    const t0 = Date.now();
    await p.keyboard.type(name, { delay: D });
    keyMs += Date.now() - t0;
    chars += name.length + 1;   // standard wpm counts the space after each word
    await p.waitForTimeout(900);
  }
  const shown = await p.evaluate(() => document.querySelector('#stats').innerText.replace(/\s+/g, ' '));
  console.log(`pace ${D} ms/key -> true speed ${Math.round(60000 / (D * 5))} wpm | page shows: ${shown} | measured typing ${Math.round(chars / 5 / ((keyMs + chars * 0) / 60000))} wpm over the keystrokes`);
  await b.close();
})();
