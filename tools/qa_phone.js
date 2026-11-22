// Phone pass: open dist/index.html the way a phone does (touch, 390 x 844 and a small 360 x 640) in the bundled
// Chromium and in WebKit (Safari's engine), and check what a visitor from a shared link does first.
//   node tools/qa_phone.js [chromium|webkit]
const pw = require('playwright-core');
const path = require('path'); const { pathToFileURL } = require('url');
const URL0 = pathToFileURL(path.join(__dirname, '..', 'dist', 'index.html')).href, SHOTS = path.join(__dirname, '..', 'shots');
const which = process.argv[2] || 'chromium';
const issues = []; let checks = 0, where = 'boot'; const notes = [];
const ok = (c, what) => { checks++; if (!c) issues.push(where + ': ' + what); return !!c; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const browser = which === 'webkit' ? await pw.webkit.launch({ headless: true }) : await pw.chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  for (const [vw, vh, tag] of [[390, 844, 'phone'], [360, 640, 'small']]) {
    const ctx = await browser.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 2, isMobile: which !== 'webkit' ? true : undefined, hasTouch: true,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1' });
    const p = await ctx.newPage(); where = tag + ' boot';
    p.on('pageerror', (e) => issues.push(where + ': script error: ' + e.message.slice(0, 160)));
    p.on('console', (m) => { if (m.type() === 'error' && !/favicon|ERR_FILE_NOT_FOUND/.test(m.text())) issues.push(where + ': console error: ' + m.text().slice(0, 160)); });
    const t0 = Date.now(); await p.goto(URL0);
    const ready = await p.waitForFunction(() => window.gyrus && window.gyrus.R && window.gyrus.R.size > 0, null, { timeout: 120000 }).then(() => true).catch(() => false);
    if (!ok(ready, 'the app did not start')) { await p.screenshot({ path: path.join(SHOTS, 'ph_' + which + '_' + tag + '_boot.png') }); await ctx.close(); continue; }
    notes.push(tag + ': ready in ' + (Date.now() - t0) + ' ms'); await sleep(2500);
    const page = () => p.evaluate(() => { const W = innerWidth, H = innerHeight, vis = (e) => { if (!e) return null; const cs = getComputedStyle(e), r = e.getBoundingClientRect(); return cs.display === 'none' || cs.visibility === 'hidden' || r.width < 2 || r.height < 2 ? null : r; };
      const pb = document.querySelector('#pbody'), txt = document.body.innerText; const off = [...document.querySelectorAll('button')].filter((b) => { const r = vis(b); return r && (r.right > W + 2 || r.left < -2) && !b.closest('[style*="overflow"]') && !b.closest('#decks'); }).map((b) => (b.innerText || b.id).trim().slice(0, 18));
      return { mode: gyrus.S.mode, sideways: document.documentElement.scrollWidth > W + 1, bad: (txt.match(/undefined|\bNaN\b|\[object Object\]/) || [null])[0], panel: !!vis(document.querySelector('#panel')), play: !!vis(document.querySelector('#play')), canvas: !!vis(document.querySelector('canvas')), off: off.slice(0, 5),
        active: document.activeElement ? document.activeElement.id || document.activeElement.tagName : '', small: [...document.querySelectorAll('button')].filter((b) => { const r = vis(b); return r && r.top < H && r.bottom > 0 && (r.width < 28 || r.height < 24); }).map((b) => (b.innerText || b.id || b.title || '?').trim().slice(0, 14)).slice(0, 6) }; });
    const basic = async () => { const s = await page(); ok(!s.sideways, 'page scrolls sideways'); ok(!s.bad, 'screen shows "' + s.bad + '"'); ok(s.canvas, 'the brain is not on screen'); ok(!s.off.length, 'buttons off the edge: ' + s.off.join(', ')); if (s.small.length) notes.push(where + ': small tap targets: ' + s.small.join(', ')); return s; };
    await basic(); await p.screenshot({ path: path.join(SHOTS, 'ph_' + which + '_' + tag + '_open.png') });
    for (const mode of ['explore', 'learn', 'type', 'find', 'quiz', 'paths']) {
      where = tag + ' ' + mode; await p.evaluate((m) => gyrus.setMode(m), mode); await sleep(900); const s = await basic(); ok(s.mode === mode, 'mode did not switch');
      if (mode === 'explore') { const c = await p.locator('canvas').first().boundingBox(); await p.touchscreen.tap(c.x + c.width * 0.5, c.y + c.height * 0.45); await sleep(900); const sel = await p.evaluate(() => (gyrus.S.sel ? gyrus.S.sel.name || true : null)); ok(sel, 'a tap on the brain selected nothing'); ok((await page()).panel, 'no card for the tapped region'); }
      if (mode === 'type' || mode === 'quiz') { const b = await p.locator('#play').boundingBox(); if (ok(b, 'no typing card')) { const wd = await p.locator('#word').boundingBox().catch(() => null); await p.touchscreen.tap(b.x + b.width / 2, wd ? wd.y + wd.height / 2 : b.y + b.height * 0.5); await sleep(500); const a = (await page()).active; ok(a === 'typer', 'tapping the typing card did not put the cursor in the answer field (' + a + ')');
          const g = await p.evaluate(() => { const w = document.querySelector('#word').getBoundingClientRect(), c = document.querySelector('#gl').getBoundingClientRect(); return { word: Math.round(w.bottom), cTop: Math.round(c.top), cBot: Math.round(c.bottom), cw: Math.round(c.width), ch: Math.round(c.height), H: innerHeight }; }); ok(g.word <= g.H * 0.56 && g.word > 0, 'the word to type sits at ' + g.word + ' of ' + g.H + ' px: a keyboard would cover it'); ok(g.cTop >= -6 && g.cBot <= g.H * 0.52, 'the brain is not fully above the keyboard (' + g.cTop + ' to ' + g.cBot + ')');
          if (mode === 'type') { const name = await p.evaluate(() => gyrus.T && gyrus.T.r && gyrus.T.r.name); if (name) { await p.keyboard.type(name, { delay: 8 }); await sleep(700); const nxt = await p.evaluate(() => gyrus.T && gyrus.T.r && gyrus.T.r.name); ok(nxt !== name, 'typing the right name did not move on'); } } } }
      await p.screenshot({ path: path.join(SHOTS, 'ph_' + which + '_' + tag + '_' + mode + '.png') });
    }
    for (const [btn, box] of [['#about', '#aboutp'], ['#progbtn', '#progp']]) { where = tag + ' dialog ' + box; await p.evaluate(() => scrollTo(0, 0)); await p.locator(btn).tap(); await sleep(400);
      const d = await p.evaluate((b) => { const e = document.querySelector(b), c = e.querySelector('[data-dclose]'), r = c && c.getBoundingClientRect(); return { open: !e.classList.contains('off'), close: r ? [Math.round(r.width), Math.round(r.height), Math.round(r.top)] : null, H: innerHeight }; }, box);
      ok(d.open, 'did not open'); if (ok(d.close, 'no Close button')) { ok(d.close[0] >= 44 && d.close[1] >= 32, 'Close button is small: ' + d.close[0] + ' x ' + d.close[1]); ok(d.close[2] >= 0 && d.close[2] < d.H, 'Close button is off screen'); await p.locator(box + ' [data-dclose]').tap(); await sleep(300); ok(await p.evaluate((b) => document.querySelector(b).classList.contains('off'), box), 'Close did not close it'); } }
    // every signal pathway: Test me must open a field to type in
    await p.evaluate(() => gyrus.setMode('paths')); await sleep(700);
    const ids = await p.evaluate(() => [...document.querySelectorAll('.pathlist [data-path]')].map((b) => b.dataset.path));
    for (const id of ids) {
      where = tag + ' pathway ' + id;
      const btn = p.locator('.pathlist [data-path="' + id + '"]'); if (!ok(await btn.count(), 'not in the list')) continue;
      await btn.scrollIntoViewIfNeeded(); await btn.tap(); await sleep(700); await basic();
      const tm = p.locator('[data-ptest="1"]');
      if (await tm.count()) {
        await tm.scrollIntoViewIfNeeded(); await tm.tap(); await sleep(600);
        const f = await p.evaluate(() => { const i = document.querySelector('#pqin'), q = document.querySelector('#pqt'); if (!i || !q) return null; const a = i.getBoundingClientRect(), b = q.getBoundingClientRect(); return { focused: document.activeElement === i, over: Math.abs(a.left - b.left) < 3 && Math.abs(a.top - b.top) < 3 && a.width >= 40, qTop: Math.round(b.top), qBottom: Math.round(b.bottom), H: innerHeight, fs: getComputedStyle(i).fontSize, ro: i.readOnly || i.disabled }; });
        if (ok(f, 'the test has no typing field')) { ok(f.focused, 'Test me did not put the cursor in the typing field'); ok(f.over, 'the typing field is not on the typing line'); ok(f.qTop >= 0 && f.qBottom <= f.H, 'the typing line is off screen (top ' + f.qTop + ')'); ok(parseFloat(f.fs) >= 16, 'field font under 16px makes an iPhone zoom in'); ok(f.qBottom <= f.H * 0.5, 'typing line at ' + f.qBottom + ' of ' + f.H + ' px: a phone keyboard would cover it'); }
        if (id === ids.find((x) => x)) await p.screenshot({ path: path.join(SHOTS, 'ph_' + which + '_' + tag + '_test.png') });
        let guard = 0, first = true;
        for (;;) { const q = await p.evaluate(() => { const q = gyrus.PQ, P = gyrus.PT.P; if (!q) return { gone: true }; if (q.end) return { end: true, right: q.right, n: P.steps.length - 1 }; const k = q.pend[0], s = P.steps[k], r = s.r && gyrus.R.get(s.r); return { name: r ? (r.title || r.name) : s.n, left: q.pend.length }; });
          if (q.gone) { ok(false, 'the test closed by itself'); break; } if (q.end) { ok(q.right === q.n - (first ? 0 : 1) || q.right === q.n, 'score ' + q.right + ' of ' + q.n); break; } if (guard++ > 30) { ok(false, 'the test did not finish'); break; }
          if (first && guard === 1 && q.left > 1) { // once per pathway: the touch buttons
            await p.locator('[data-pqshow]').tap(); await sleep(350); ok(await p.evaluate(() => gyrus.PQ && gyrus.PQ.reveal != null), 'Show answer did nothing'); await p.locator('[data-pqnext]').tap(); await sleep(350); ok(await p.evaluate(() => gyrus.PQ && gyrus.PQ.reveal == null && document.activeElement === gyrus.pqin), 'after Continue the cursor left the typing field'); first = false; continue; }
          await p.keyboard.type(q.name, { delay: 6 }); let moved = false; for (let w = 0; w < 20 && !moved; w++) { await sleep(70); moved = await p.evaluate((l) => !gyrus.PQ || gyrus.PQ.end || gyrus.PQ.pend.length < l, q.left); }
          if (!ok(moved, 'typing "' + q.name + '" was not accepted')) { await p.locator('[data-pqshow]').tap().catch(() => {}); await sleep(200); await p.locator('[data-pqnext]').tap().catch(() => {}); await sleep(200); } }
        await p.locator('[data-ptest="0"]').first().tap().catch(() => {}); await sleep(300);
        ok(await p.evaluate(() => document.activeElement !== gyrus.pqin), 'the typing field kept the cursor after the test');
      }
      const all = p.locator('[data-pathall]'); if (await all.count()) { await all.first().scrollIntoViewIfNeeded(); await all.first().tap(); await sleep(350); } else { await p.evaluate(() => gyrus.setMode('paths')); await sleep(350); }
    }
    await ctx.close();
  }
  await browser.close();
  console.log(which + ' phone pass: ' + checks + ' checks, ' + issues.length + ' issues');
  const by = {}; issues.forEach((i) => { const k = i.replace(/^(phone|small) /, '').replace(/"[^"]*"/g, '"…"').replace(/pathway \w+/, 'pathway *').replace(/\d+/g, 'N'); (by[k] = by[k] || []).push(i); });
  Object.entries(by).sort((a, b) => b[1].length - a[1].length).slice(0, 25).forEach(([k, v]) => console.log('  ' + String(v.length).padStart(3) + ' x ' + v[0].slice(0, 200)));
  [...new Set(notes)].slice(0, 30).forEach((n) => console.log('  note: ' + n.slice(0, 200)));
})().catch((e) => { console.error('ERR', e.message.split('\n')[0]); process.exit(1); });
