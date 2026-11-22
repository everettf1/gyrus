// QA pass 2 (browser): drive dist/index.html in the bundled Chromium and record anything wrong.
//   node tools/qa_run.js <part>      part = explore | type | modes | paths | misc | layout
// Each part writes shots/qa_<part>.json  {checks: n, issues: [{where, what}], notes: [...]}  and prints a summary.
const { chromium } = require('playwright-core');
const fs = require('fs'); const path = require('path'); const { pathToFileURL } = require('url');
const EXE = process.env.CHROMIUM_PATH || undefined;
const URL0 = pathToFileURL(path.join(__dirname, '..', 'dist', 'index.html')).href;
const SHOTS = path.join(__dirname, '..', 'shots');
const part = process.argv[2] || 'explore';
const issues = []; const notes = []; let checks = 0; let where = 'boot';
const issue = (what, w) => { issues.push({ where: w || where, what: String(what).slice(0, 300) }); };
const ok = (cond, what, w) => { checks++; if (!cond) issue(what, w); return !!cond; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const DECKS = ['lobes', 'areas', 'networks', 'gyri', 'sulci', 'deep', 'thalamus', 'brainstem', 'tracts'];
const VIEWS = ['lateral', 'medial', 'superior', 'inferior', 'anterior', 'posterior'];

async function open(browser, vw, vh) {
  const ctx = await browser.newContext({ viewport: { width: vw || 1440, height: vh || 900 } });
  const p = await ctx.newPage();
  p.on('pageerror', (e) => issue('script error: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error' && !/favicon|net::ERR_FILE_NOT_FOUND.*favicon/.test(m.text())) issue('console error: ' + m.text()); });
  const t0 = Date.now();
  await p.goto(URL0);
  await p.waitForFunction(() => window.gyrus && window.gyrus.R && window.gyrus.R.size > 0, null, { timeout: 120000 });
  p._loadMs = Date.now() - t0;
  await p.waitForTimeout(2500);
  return p;
}
const BADTXT = /undefined|\bNaN\b|\[object Object\]|Infinity/;

// ---------------------------------------------------------------------------------------------- explore
async function partExplore(browser) {
  const p = await open(browser);
  notes.push('load to ready: ' + p._loadMs + ' ms');
  const ids = await p.evaluate(() => [...gyrus.R.keys()]);
  ok(ids.length === 186, 'expected 186 regions, found ' + ids.length);
  await p.evaluate(() => gyrus.setMode('explore')); await sleep(600);
  let nStim = 0, nProb = 0, nFig = 0;
  for (const id of ids) {
    where = 'explore ' + id;
    const r = await p.evaluate((rid) => {
      gyrus.select(rid); const R = gyrus.R.get(rid), pb = document.querySelector('#pbody'), txt = pb.innerText;
      const secs = [...pb.querySelectorAll('section.sec h3')].map((h) => h.innerText.trim());
      return { sel: gyrus.S.sel && gyrus.S.sel.id, title: (pb.querySelector('.ptitle') || {}).innerText || '', bad: (txt.match(/undefined|\bNaN\b|\[object Object\]|Infinity/) || [null])[0],
        nEv: pb.querySelectorAll('details.evi').length, exp: (R.evidence || []).length, figs: pb.querySelectorAll('figure img').length, stim: !!pb.querySelector('[data-stim]'), hasStim: !!(R.stimulation && R.stimulation.effect),
        prob: !!pb.querySelector('[data-prob]'), fi: !!gyrus.frameInfo(R), secs, len: txt.length, name: R.name, ttl: R.title || '', refs: pb.querySelectorAll('.refs li').length, see: pb.querySelectorAll('[data-see]').length, seeExp: (R.see_also || []).length };
    }, id);
    ok(r.sel === id, 'selecting it did not make it the selection (got ' + r.sel + ')');
    ok(r.title && r.title.toLowerCase().includes((r.ttl || r.name).toLowerCase().slice(0, 12)), 'panel title "' + r.title + '" does not match the region name "' + (r.ttl || r.name) + '"');
    ok(!r.bad, 'panel text contains "' + r.bad + '"');
    ok(r.nEv === r.exp, 'evidence cards shown ' + r.nEv + ' but the region has ' + r.exp);
    ok(r.fi, 'no camera framing: nothing to draw for this region');
    ok(r.len > 600, 'panel text is very short (' + r.len + ' characters)');
    ok(r.stim === r.hasStim, 'stimulation section ' + (r.stim ? 'shown' : 'missing') + ' but data says ' + r.hasStim);
    ok(r.refs > 0, 'no references shown');
    ok(r.see === r.seeExp, 'see-also buttons ' + r.see + ' but data lists ' + r.seeExp);
    nFig += r.figs;
    if (r.stim) { nStim++; await p.click('#pbody [data-stim]').catch((e) => issue('stimulate button: ' + e.message.split('\n')[0])); await sleep(120); }
    if (r.prob) { nProb++; await p.click('#pbody [data-prob]').catch((e) => issue('variability button: ' + e.message.split('\n')[0])); await sleep(150); const on = await p.evaluate(() => gyrus.S.prob); ok(on === id, 'variability map did not turn on'); await p.click('#pbody [data-prob]').catch(() => {}); await sleep(80); }
  }
  notes.push('regions opened ' + ids.length + ', stimulation run ' + nStim + ', variability maps toggled ' + nProb + ', figures in cards ' + nFig);
  // every figure file loads
  where = 'figures';
  const figs = await p.evaluate(async () => {
    const srcs = new Set(); for (const r of gyrus.R.values()) { for (const e of r.evidence || []) if (e.fig) srcs.add(e.fig.src); if (r.stimulation && r.stimulation.fig) srcs.add(r.stimulation.fig.src); }
    for (const T of gyrus.TOPICS) for (const s of T.steps) for (const e of s.ev || []) if (e.fig) srcs.add(e.fig.src);
    const bad = []; let small = 0;
    await Promise.all([...srcs].map((s) => new Promise((res) => { const im = new Image(); im.onload = () => { if (im.naturalWidth < 200) small++; res(); }; im.onerror = () => { bad.push(s); res(); }; im.src = s; })));
    return { n: srcs.size, bad, small };
  });
  ok(figs.bad.length === 0, 'figure files that do not load: ' + figs.bad.join(', '));
  notes.push('figure files loaded ' + (figs.n - figs.bad.length) + ' of ' + figs.n + (figs.small ? ', under 200 px wide: ' + figs.small : ''));
  // search box: every region is findable by its name
  where = 'search';
  let miss = 0;
  for (const id of ids) {
    const nm = await p.evaluate((rid) => gyrus.R.get(rid).name, id);
    await p.fill('#q', nm); await sleep(25);
    const first = await p.evaluate(() => { const b = document.querySelector('#res button, #qres button, .results button'); return b ? b.innerText.replace(/\s+/g, ' ') : null; });
    checks++; if (first === null) { miss++; if (miss <= 5) issue('search for "' + nm + '" shows no results'); }
  }
  await p.fill('#q', '');
  if (miss > 5) issue('search: ' + miss + ' region names in total show no results');
  await p.context().close();
}

// ---------------------------------------------------------------------------------------------- type
async function typeName(p, name) { await p.focus('#typer').catch(() => {}); await p.keyboard.type(name, { delay: 6 }); }
const tstate = (p) => p.evaluate(() => ({ id: gyrus.T && !gyrus.T.done ? gyrus.T.r.id : null, name: gyrus.T ? gyrus.T.r.name : '', word: document.querySelector('#word').innerText.replace(/\s+/g, ' ').slice(0, 400), stats: (document.querySelector('#stats') || { innerText: '' }).innerText.replace(/\s+/g, ' ') }));
async function waitAdvance(p, prevId, ms) {
  const t0 = Date.now();
  while (Date.now() - t0 < (ms || 4000)) { const s = await tstate(p); if (s.id && s.id !== prevId) return s; if (!s.id && /first try|right out of|Test again|Go again|missed/i.test(s.word)) return Object.assign(s, { end: true }); await sleep(50); }
  return null;
}
async function partType(browser) {
  const p = await open(browser);
  for (const deck of DECKS) {
    where = 'type test ' + deck;
    await p.evaluate((d) => { gyrus.setMode('type'); gyrus.setDeck(d); gyrus.setSub('test'); }, deck); await sleep(500);
    await p.click('[data-len="all"]').catch(() => issue('no "All" length button in Test')); await sleep(600);
    const size = await p.evaluate((d) => [...gyrus.R.values()].filter((r) => r.deck === d).length, deck);
    const seen = new Set(); let stuck = 0, end = null;
    for (let i = 0; i < size + 4; i++) {
      const s = await tstate(p); if (!s.id) { end = s; break; }
      if (seen.has(s.id)) issue('the same region was asked twice in one test: ' + s.name);
      seen.add(s.id);
      await typeName(p, s.name);
      const nx = await waitAdvance(p, s.id, 4500);
      checks++;
      if (!nx) { stuck++; issue('typing "' + s.name + '" did not auto-submit'); await p.keyboard.press('Enter'); await sleep(700); const s2 = await tstate(p); if (s2.id === s.id) { await p.keyboard.down('Shift'); await p.keyboard.press('Enter'); await p.keyboard.up('Shift'); await sleep(700); } }
      else if (nx.end) { end = nx; break; }
    }
    ok(seen.size === size, 'test covered ' + seen.size + ' of ' + size + ' regions');
    const fin = end || await tstate(p);
    ok(/100\s*%/.test(fin.word) || stuck > 0, 'results after an all-correct test do not show 100%: ' + fin.word.slice(0, 160));
    ok(!BADTXT.test(fin.word + fin.stats), 'results or stats contain a bad value: ' + (fin.word + ' ' + fin.stats).slice(0, 200));
    notes.push(deck + ': ' + seen.size + '/' + size + ' typed in Test, stats: ' + fin.stats.slice(0, 80));
  }
  // practice: name shown, auto-advance, hint, skip, pause
  where = 'type practice';
  await p.evaluate(() => { gyrus.setDeck('areas'); gyrus.setSub('practice'); }); await sleep(700);
  for (let i = 0; i < 6; i++) { const s = await tstate(p); ok(s.word.toLowerCase().includes(s.name.toLowerCase().slice(0, 6)), 'practice does not show the name to type: "' + s.word.slice(0, 60) + '" vs ' + s.name); await typeName(p, s.name); ok(await waitAdvance(p, s.id), 'practice: "' + s.name + '" did not advance'); }
  { const s = await tstate(p); await p.keyboard.type('?'); await sleep(200); await p.keyboard.down('Shift'); await p.keyboard.press('Enter'); await p.keyboard.up('Shift'); ok(await waitAdvance(p, s.id, 5000), 'Shift+Enter did not skip'); }
  { await p.keyboard.press('Escape'); await sleep(400); const paused = await p.evaluate(() => document.body.className + ' ' + (document.querySelector('#focushint') || {}).innerText); notes.push('after Esc: ' + paused.replace(/\s+/g, ' ').slice(0, 80)); await p.keyboard.press('Escape'); await sleep(300); }
  // recall: wrong answer, review, keep going
  where = 'type recall';
  await p.evaluate(() => { gyrus.setDeck('lobes'); gyrus.setSub('recall'); }); await sleep(700);
  for (let i = 0; i < 3; i++) { const s = await tstate(p); await typeName(p, s.name); ok(await waitAdvance(p, s.id), 'recall: "' + s.name + '" did not advance'); }
  { const s = await tstate(p); await typeName(p, 'zzzz'); await p.keyboard.press('Enter'); await sleep(900); const s2 = await tstate(p); ok(!BADTXT.test(s2.stats), 'recall stats bad after a wrong answer: ' + s2.stats); await typeName(p, s2.name || s.name); await sleep(900); }
  { const has = await p.evaluate(() => { const b = document.querySelector('#revlink'); return b && !b.hidden; }); ok(has, 'no "Review so far" link after answers in endless recall'); if (has) { await p.click('#revlink'); await sleep(900); const w = (await tstate(p)).word; ok(/missed|first try|So far/i.test(w), 'review screen did not open: ' + w.slice(0, 100)); await p.keyboard.press('Enter'); await sleep(800); ok((await tstate(p)).id, 'Enter on the review screen did not resume'); } }
  // timed lengths in practice: 10 items ends with results
  where = 'type 10 items';
  await p.evaluate(() => { gyrus.setDeck('gyri'); gyrus.setSub('practice'); }); await sleep(500);
  if (await p.$('[data-plen="10"]')) {
    await p.click('[data-plen="10"]'); await sleep(600); let end = null;
    for (let i = 0; i < 12; i++) { const s = await tstate(p); if (!s.id) { end = s; break; } await typeName(p, s.name); const nx = await waitAdvance(p, s.id); if (!nx) { issue('10-item round: "' + s.name + '" did not advance'); break; } if (nx.end) { end = nx; break; } }
    ok(end, '10-item round did not reach a results screen'); if (end) ok(!BADTXT.test(end.word), 'results contain a bad value: ' + end.word.slice(0, 160));
    await p.click('[data-plen="60"]').catch(() => {}); await sleep(500);
    { const s = await tstate(p); await typeName(p, s.name); await waitAdvance(p, s.id); await sleep(1300); const st = (await tstate(p)).stats; ok(/\d+:\d\d|\b\d+ ?s\b/.test(st), '60 s round shows no clock in the stats: ' + st); }
    await p.click('[data-plen="0"]').catch(() => {}); await p.click('[data-plen="endless"]').catch(() => {});
  } else issue('no length buttons in practice');
  // rush
  where = 'type rush';
  await p.evaluate(() => { gyrus.setDeck('lobes'); gyrus.setSub('rush'); }); await sleep(900);
  for (let i = 0; i < 4; i++) { const s = await tstate(p); if (!s.id) { issue('rush has no target'); break; } await typeName(p, s.name); const nx = await waitAdvance(p, s.id, 5000); if (!nx) { issue('rush: "' + s.name + '" did not advance'); break; } }
  { const st = await tstate(p); ok(!BADTXT.test(st.stats + st.word), 'rush shows a bad value: ' + st.stats); notes.push('rush stats: ' + st.stats.slice(0, 90)); }
  // daily
  where = 'type daily';
  await p.evaluate(() => { gyrus.setDeck('areas'); gyrus.setSub('daily'); }); await sleep(900);
  { let end = null; for (let i = 0; i < 40; i++) { const s = await tstate(p); if (!s.id) { end = s; break; } await typeName(p, s.name); const nx = await waitAdvance(p, s.id); if (!nx) { issue('daily: "' + s.name + '" did not advance'); break; } if (nx.end) { end = nx; break; } }
    ok(end, 'daily did not reach a results screen in 40 items'); if (end) { ok(!BADTXT.test(end.word), 'daily results contain a bad value: ' + end.word.slice(0, 200)); notes.push('daily result: ' + end.word.slice(0, 140)); } }
  // persistence across a reload
  where = 'persistence';
  const known = await p.evaluate(() => document.body.innerText.match(/(\d+)\s*\/\s*186 known/)); const k0 = known ? +known[1] : -1;
  await p.reload(); await p.waitForFunction(() => window.gyrus && window.gyrus.R && window.gyrus.R.size > 0, null, { timeout: 120000 }); await sleep(2000);
  const known2 = await p.evaluate(() => document.body.innerText.match(/(\d+)\s*\/\s*186 known/)); const k1 = known2 ? +known2[1] : -2;
  ok(k0 === k1 && k0 > 0, 'known count before reload ' + k0 + ', after ' + k1);
  notes.push('known count kept across reload: ' + k1);
  await p.context().close();
}

// ---------------------------------------------------------------------------------------------- learn, find, quiz
async function partModes(browser) {
  const p = await open(browser);
  for (const deck of DECKS) {
    where = 'learn ' + deck;
    await p.evaluate((d) => { gyrus.setMode('learn'); gyrus.setDeck(d); }, deck); await sleep(500);
    const n = await p.evaluate((d) => [...gyrus.R.values()].filter((r) => r.deck === d).length, deck);
    const seen = new Set();
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < 8; k++) await p.evaluate(() => gyrus.learnAdvance && document.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true })));
      const s = await p.evaluate(() => { const pb = document.querySelector('#pbody'); return { id: gyrus.S.sel && gyrus.S.sel.id, bad: (pb.innerText.match(/undefined|\bNaN\b|\[object Object\]/) || [null])[0], more: !!pb.querySelector('[data-learnmore]'), len: pb.innerText.length }; });
      if (s.id) seen.add(s.id); ok(!s.bad, 'learn panel contains "' + s.bad + '" at ' + s.id); ok(s.len > 300, 'learn panel nearly empty at ' + s.id);
      await p.evaluate(() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))); await sleep(15);
    }
    ok(seen.size >= n - 1, 'learn stepped through ' + seen.size + ' of ' + n);
    // cover names, learn more, back
    await p.click('[data-cover]').catch(() => issue('no cover-names button')); await sleep(200);
    const cov = await p.evaluate(() => document.querySelector('#pbody .ptitle').innerText); ok(/Which region/i.test(cov), 'cover names did not hide the title: ' + cov);
    await p.evaluate(() => document.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }))); await sleep(150);
    await p.click('[data-cover]').catch(() => {}); await sleep(150);
    const before = await p.evaluate(() => gyrus.S.sel && gyrus.S.sel.id);
    if (await p.$('[data-learnmore]')) { await p.click('[data-learnmore]'); await sleep(500); const m = await p.evaluate(() => gyrus.S.mode + ':' + (gyrus.S.sel && gyrus.S.sel.id)); ok(m === 'explore:' + before, 'Learn more opened ' + m + ' instead of explore:' + before);
      if (await p.$('[data-backlearn]')) { await p.click('[data-backlearn]'); await sleep(600); const b = await p.evaluate(() => gyrus.S.mode + ':' + (gyrus.S.sel && gyrus.S.sel.id)); ok(b === 'learn:' + before, 'Back to Learn returned to ' + b); } else issue('no Back to Learn link'); } else issue('no Learn more button');
  }
  // quiz
  for (const deck of DECKS) {
    where = 'quiz ' + deck;
    await p.evaluate((d) => { gyrus.setMode('quiz'); gyrus.setDeck(d); }, deck); await sleep(700);
    for (let i = 0; i < 6; i++) {
      const s = await p.evaluate(() => ({ id: gyrus.T && !gyrus.T.done ? gyrus.T.r.id : null, name: gyrus.T ? gyrus.T.r.name : '', q: document.querySelector('#clue').innerText.replace(/\s+/g, ' '), play: document.querySelector('#play').innerText.replace(/\s+/g, ' ').slice(0, 300) }));
      if (!s.id) { issue('quiz has no question: ' + s.play.slice(0, 100)); break; }
      ok(s.q.length > 20, 'quiz question text is missing or short: "' + s.q + '"');
      ok(!new RegExp('\\b' + s.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i').test(s.q), 'quiz question gives away the answer "' + s.name + '": ' + s.q.slice(0, 120));
      await typeName(p, s.name);
      let acc = false; for (let w = 0; w < 25 && !acc; w++) { await sleep(80); acc = await p.evaluate(() => !!(gyrus.T && gyrus.T.done)); }
      ok(acc, 'quiz did not accept the right answer "' + s.name + '" without Enter');
      const shown = await p.evaluate(() => document.querySelector('#pbody').innerText.length); ok(shown > 300, 'quiz did not show the region write-up after the answer');
      await p.keyboard.press('Enter'); let adv = false;
      for (let w = 0; w < 30 && !adv; w++) { await sleep(100); adv = await p.evaluate((q0) => !!(gyrus.T && !gyrus.T.done) && document.querySelector('#clue').innerText.replace(/\s+/g, ' ') !== q0, s.q); }
      ok(adv, 'quiz: Enter did not bring the next question after "' + s.name + '"');
      if (!adv) break;
    }
  }
  // Find is covered region by region in the separate 'find' part
  await p.context().close();
}

// ---------------------------------------------------------------------------------------------- pathways
async function partPaths(browser) {
  const p = await open(browser);
  await p.evaluate(() => gyrus.setMode('paths')); await sleep(900);
  const list = await p.evaluate(() => [...document.querySelectorAll('.pathlist [data-path]')].map((b) => b.dataset.path));
  const heads = await p.evaluate(() => [...document.querySelectorAll('.pathlist h4')].map((h) => h.innerText).join(' | '));
  notes.push('pathway list: ' + list.length + ' entries; groups: ' + heads);
  for (const id of list) {
    where = 'pathway ' + id;
    await p.evaluate((x) => { gyrus.startPath(x); gyrus.pathGo(0); }, id); await sleep(350);
    const info = await p.evaluate(() => { const P = gyrus.PT && gyrus.PT.P; if (!P) return null; return { n: P.steps.length, sys: !!P.sys, topic: !!P.topic, maps: P.maps || [], circuit: !!P.circuit, timing: !!P.timing,
      unresolved: P.steps.map((s, k) => (!P.topic && !gyrus.PT.pts[k] ? k + 1 : 0)).filter(Boolean), badRegion: P.steps.map((s) => (s.r && !gyrus.R.get(s.r) ? s.r : null)).filter(Boolean), ev: P.steps.map((s) => (s.ev || []).length), rs: P.steps.map((s) => (s.rs || []).length) }; });
    if (!ok(info, 'pathway did not start')) continue;
    ok(info.unresolved.length === 0, 'stations with no position: ' + info.unresolved.join(','));
    ok(info.badRegion.length === 0, 'stations naming unknown regions: ' + info.badRegion.join(','));
    for (let k = 0; k < info.n; k++) {
      await p.evaluate((kk) => gyrus.pathGo(kk), k); await sleep(info.topic ? 140 : 60);
      const s = await p.evaluate(() => { const pb = document.querySelector('#pbody'); return { i: gyrus.PT.i, bad: (pb.innerText.match(/undefined|\bNaN\b|\[object Object\]/) || [null])[0], nEv: pb.querySelectorAll('details.evi').length, limit: !!pb.querySelector('.tlimit'), list: !!pb.querySelector('.tbody ul'), figs: pb.querySelectorAll('figure img').length, chips: pb.querySelectorAll('[data-topicsee]').length, circ: !!pb.querySelector('svg.circ'), bars: pb.querySelectorAll('.bars .br').length, len: pb.innerText.length }; });
      ok(s.i === k, 'step ' + (k + 1) + ' did not become current'); ok(!s.bad, 'step ' + (k + 1) + ' panel contains "' + s.bad + '"');
      if (info.topic) { ok(s.nEv === info.ev[k], 'step ' + (k + 1) + ': evidence cards ' + s.nEv + ' vs ' + info.ev[k]); ok(s.limit || s.list, 'step ' + (k + 1) + ' has no limits box or list'); ok(s.chips === info.rs[k], 'step ' + (k + 1) + ': Explore chips ' + s.chips + ' vs regions ' + info.rs[k]); }
      if (info.circuit && k === 0) ok(s.circ, 'circuit diagram missing'); if (info.timing && k === 0) ok(s.bars > 0, 'arrival-time bars missing');
    }
    if (info.topic) { // open a region from the tour and come back
      const k = info.rs.findIndex((x) => x > 0); if (k >= 0) { await p.evaluate((kk) => gyrus.pathGo(kk), k); await sleep(200); await p.click('[data-topicsee]'); await sleep(600); const m = await p.evaluate(() => gyrus.S.mode); ok(m === 'explore', 'Open in Explore went to ' + m);
        if (await p.$('[data-backtour]')) { await p.click('[data-backtour]'); await sleep(700); const b = await p.evaluate(() => gyrus.S.mode + ':' + (gyrus.PT && gyrus.PT.P.id) + ':' + (gyrus.PT && gyrus.PT.i)); ok(b === 'paths:' + id + ':' + k, 'Back to the tour returned to ' + b); } else issue('no Back to the tour link'); }
    } else if (info.sys) { // receptor maps
      for (const m of info.maps) { await p.evaluate((kk) => gyrus.pathGo(kk), 0); const btn = await p.$('[data-chem="' + m + '"]'); if (!ok(btn, 'no button for map ' + m)) continue; if ((await btn.getAttribute('aria-pressed')) !== 'true') await btn.click(); let n = 0; for (let w = 0; w < 30 && !n; w++) { await sleep(120); n = await p.evaluate(() => document.querySelectorAll('#pbody .bars .br').length); }
        ok(n >= 16, 'map ' + m + ': density bars ' + n); const bad = await p.evaluate(() => (document.querySelector('#pbody').innerText.match(/undefined|\bNaN\b/) || [null])[0]); ok(!bad, 'map ' + m + ' panel contains ' + bad);
        const b2 = await p.$('[data-chem="' + m + '"]'); if (b2) await b2.click(); await sleep(150); }
    } else { // test me, answering every station correctly
      const has = await p.$('[data-ptest="1"]'); if (!ok(has, 'no Test me button')) continue;
      await p.evaluate(() => gyrus.pathGo(0)); await p.click('[data-ptest="1"]'); await sleep(400); let guard = 0;
      for (;;) { const q = await p.evaluate(() => { const q = gyrus.PQ, P = gyrus.PT.P; if (!q) return { gone: true }; if (q.end) return { end: true, right: q.right, n: P.steps.length - 1 }; const k = q.pend[0], s = P.steps[k], r = s.r && gyrus.R.get(s.r); return { k, name: r ? r.name : s.n, left: q.pend.length }; });
        if (q.gone) { issue('test closed by itself'); break; } if (q.end) { ok(q.right === q.n, 'all-correct test scored ' + q.right + ' of ' + q.n); break; } if (guard++ > 30) { issue('test did not finish'); break; }
        await p.keyboard.type(q.name, { delay: 5 }); let moved = false; for (let w = 0; w < 20; w++) { await sleep(80); const l = await p.evaluate(() => (gyrus.PQ ? (gyrus.PQ.end ? -1 : gyrus.PQ.pend.length) : -2)); if (l !== q.left) { moved = true; break; } }
        checks++; if (!moved) { issue('Test me: typing "' + q.name + '" was not accepted'); await p.keyboard.press('Enter'); await sleep(150); await p.keyboard.press('Enter'); await sleep(150); await p.keyboard.press('Enter'); await sleep(250); } }
      await p.keyboard.press('Escape'); await sleep(300); ok(await p.evaluate(() => !gyrus.PQ), 'Esc did not leave the test');
    }
    if (await p.$('[data-pathall]')) { await p.click('[data-pathall]'); await sleep(250); } else await p.evaluate(() => gyrus.setMode('paths'));
  }
  await p.context().close();
}

// ---------------------------------------------------------------------------------------------- controls and the rest
async function partMisc(browser) {
  const p = await open(browser);
  const setRange = (sel, v) => p.evaluate(([s, val]) => { const e = document.querySelector(s); e.value = val; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); return e.min + '..' + e.max; }, [sel, v]);
  await p.evaluate(() => { gyrus.setMode('explore'); gyrus.select('hippocampus'); }); await sleep(600);
  where = 'views'; for (const v of VIEWS) { await p.click('[data-view="' + v + '"]'); await sleep(450); ok((await p.evaluate(() => gyrus.S.view)) === v, 'view button ' + v + ' did not set the view'); }
  where = 'hemispheres'; for (const h of ['left', 'right', 'both']) { await p.click('[data-hemi="' + h + '"]'); await sleep(250); ok((await p.evaluate(() => gyrus.S.hemi)) === h, 'hemisphere button ' + h + ' did not apply'); }
  where = 'sliders'; notes.push('cortex range ' + (await setRange('#cortex', 0.3)) + ', inflate ' + (await setRange('#inflate', 1)) + ', slice ' + (await setRange('#slice', 0))); await sleep(500);
  ok(Math.abs((await p.evaluate(() => gyrus.S.cortex)) - 0.3) < 0.36, 'cortex opacity slider did not apply'); await setRange('#inflate', 0); await setRange('#cortex', 1); await sleep(300);
  where = 'cuts';
  for (const ax of ['sagittal', 'axial', 'coronal', 'sagittal', 'coronal', 'axial']) { await p.click('[data-axis="' + ax + '"]'); await sleep(700); const s = await p.evaluate(() => ({ ax: gyrus.S.axis, sl: gyrus.S.slice, mri: !![...document.querySelectorAll('canvas')].find((c) => c.id !== 'gl' && c.getBoundingClientRect().width > 80), txt: document.body.innerText.match(/(Sagittal|Horizontal|Coronal) MRI\s*[xyz] = -?\d+ mm/) }));
    ok(s.ax === ax && s.sl > 0, 'cut ' + ax + ' did not turn on (axis ' + s.ax + ', slice ' + s.sl + ')'); ok(s.txt, 'cut ' + ax + ': no 2D MRI panel label');
    for (const v of [0.15, 0.5, 0.85]) { await setRange('#slice', v); await sleep(200); } }
  for (const id of ['precuneus', 'thalamus', 'cerebellum', 'corpus_callosum', 'area_mt', 'pons']) { await p.evaluate((x) => gyrus.select(x), id); await sleep(450); const sl = await p.evaluate(() => gyrus.S.slice); ok(sl > 0, 'cut turned off when selecting ' + id); }
  { const ax = await p.evaluate(() => gyrus.S.axis); await p.click('[data-axis="' + ax + '"]'); await sleep(500); ok((await p.evaluate(() => gyrus.S.slice)) <= 0, 'pressing the active cut button did not turn the cut off'); }
  where = 'blood supply';
  await p.click('#terrbtn'); await sleep(900); ok(await p.evaluate(() => gyrus.S.terr), 'Blood supply did not turn on');
  { const n = await p.evaluate(() => document.querySelectorAll('#pbody [data-terr]').length); ok(n >= 10, 'territory buttons: ' + n); for (let i = 0; i < n; i++) { const okc = await p.evaluate((k) => { const b = document.querySelectorAll('#pbody [data-terr]')[k]; if (!b) return false; b.click(); return true; }, i); await sleep(120); const s = await p.evaluate(() => ({ bad: (document.querySelector('#pbody').innerText.match(/undefined|\bNaN\b/) || [null])[0], sel: !!gyrus.S.terrSel, len: document.querySelector('#pbody').innerText.length })); ok(okc && s.sel && !s.bad && s.len > 150, 'territory ' + (i + 1) + ' panel problem ' + JSON.stringify(s)); await p.evaluate(() => { const a = document.querySelector('#pbody [data-terrall]'); if (a) a.click(); }); await sleep(80); } }
  await p.click('#terrbtn'); await sleep(500); ok(!(await p.evaluate(() => gyrus.S.terr)), 'Blood supply did not turn off');
  where = 'function search';
  for (const term of ['smell', 'memory', 'language', 'fear', 'pain', 'faces', 'reward', 'attention', 'movement', 'hearing', 'vision', 'emotion', 'speech', 'reading', 'sleep']) {
    await p.fill('#q', term); await sleep(250); const res = await p.evaluate(() => ({ fn: document.querySelectorAll('[data-fn]').length, any: document.querySelectorAll('#res li, .results li, ul li button').length }));
    if (res.fn) { await p.evaluate(() => document.querySelector('[data-fn]').click()); await sleep(500); const s = await p.evaluate(() => ({ fn: gyrus.S.fn, bad: (document.querySelector('#pbody').innerText.match(/undefined|\bNaN\b/) || [null])[0], len: document.querySelector('#pbody').innerText.length })); ok(s.fn != null && !s.bad && s.len > 100, 'function map "' + term + '" panel problem ' + JSON.stringify(s)); checks++; }
    else notes.push('function search: no function map offered for "' + term + '"');
  }
  await p.fill('#q', ''); await p.keyboard.press('Escape'); await p.evaluate(() => { gyrus.S.fn = null; gyrus.setMode('explore'); }); await sleep(300);
  where = 'progress and about';
  await p.click('#progbtn'); await sleep(700); { const t = await p.evaluate(() => document.body.innerText); ok(!/undefined|\bNaN\b/.test(t), 'Progress page contains a bad value'); notes.push('progress page: ' + (t.match(/\d+\s*\/\s*186 known/) || [''])[0]); }
  await p.keyboard.press('Escape'); await sleep(300); await p.click('#about'); await sleep(700);
  { const s = await p.evaluate(() => ({ refs: document.querySelectorAll('#aboutrefs li').length, txt: document.body.innerText.length, bad: /undefined|\bNaN\b/.test((document.querySelector('#aboutrefs') || document.body).innerText) })); ok(s.refs >= 12 && !s.bad, 'About: references ' + s.refs + (s.bad ? ', bad value' : '')); notes.push('About references listed: ' + s.refs); }
  await p.keyboard.press('Escape'); await sleep(300);
  await p.click('#helpbtn').catch(() => issue('help button not clickable')); await sleep(500); await p.keyboard.press('Escape'); await sleep(200);
  where = 'shortcuts';
  await p.evaluate(() => { gyrus.setMode('explore'); gyrus.select('insula'); document.activeElement && document.activeElement.blur(); }); await sleep(400);
  await p.keyboard.press('2'); await sleep(500); ok((await p.evaluate(() => gyrus.S.view)) === 'medial', 'key 2 did not switch to the medial view');
  await p.keyboard.press('h'); await sleep(250); ok((await p.evaluate(() => gyrus.S.hemi)) !== 'both', 'key h did not change the hemisphere'); await p.keyboard.press('h'); await p.keyboard.press('h'); await sleep(200);
  { const i0 = await p.evaluate(() => gyrus.S.inflate); await p.keyboard.press('i'); await sleep(300); const i1 = await p.evaluate(() => gyrus.S.inflate); ok((i0 > 0.5) !== (i1 > 0.5), 'key i did not toggle inflation (' + i0 + ' -> ' + i1 + ')'); await p.keyboard.press('i'); await sleep(300); }
  await p.keyboard.press('/'); await sleep(250); ok((await p.evaluate(() => document.activeElement && document.activeElement.id)) === 'q', 'key / did not focus the search box'); await p.keyboard.press('Escape'); await p.evaluate(() => document.activeElement && document.activeElement.blur());
  { const m0 = await p.evaluate(() => gyrus.S.mode); await p.keyboard.press('Tab'); await sleep(500); const m1 = await p.evaluate(() => gyrus.S.mode); ok(m0 !== m1, 'Tab did not move to the next mode (stayed on ' + m1 + ')'); }
  where = 'mode buttons';
  for (const m of ['type', 'learn', 'explore', 'find', 'quiz', 'paths']) { await p.click('[data-mode="' + m + '"]'); await sleep(600); ok((await p.evaluate(() => gyrus.S.mode)) === m, 'mode button ' + m + ' did not switch'); for (const d of DECKS) { await p.click('[data-deck="' + d + '"]'); await sleep(m === 'paths' ? 120 : 260); checks++; } }
  where = 'reset'; await p.click('[data-mode="explore"]'); await p.click('#reset'); await sleep(600); await p.click('#snd'); await sleep(100); await p.click('#snd'); await p.click('#zin'); await p.click('#zout'); await sleep(300);
  await p.context().close();
}

// ---------------------------------------------------------------------------------------------- layout
async function partLayout(browser) {
  const sizes = [[1920, 1080], [1440, 900], [1280, 720], [1100, 800], [1024, 768], [1010, 700], [940, 700], [820, 1180], [390, 844]];
  const lay = () => { const W = innerWidth, H = innerHeight, out = []; if (document.documentElement.scrollWidth > W + 1) out.push('page scrolls sideways (' + document.documentElement.scrollWidth + ' > ' + W + ')');
    const vis = (e) => { if (!e) return null; const cs = getComputedStyle(e), r = e.getBoundingClientRect(); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0 || r.width < 2 || r.height < 2) return null; return r; };
    const names = { '#prog': 'known counter', '#navwrap': 'mode menu', '#decks': 'deck menu', '#panel': 'text panel', '#play': 'typing card', '#side': 'side controls', '#rail': 'view controls', '#leftcol': 'left column', '#helpbar': 'help bar', '#qbox': 'search box', '#mri2d': '2D MRI panel', '#top': 'header' }; const boxes = {};
    for (const s in names) { let r = vis(document.querySelector(s)); if (!r) continue; if (s === '#decks' || s === '#navwrap') { const bs = [...document.querySelectorAll(s + ' button')].map(vis).filter(Boolean); if (bs.length) r = { left: Math.min(...bs.map((b) => b.left)), right: Math.max(...bs.map((b) => b.right)), top: Math.min(...bs.map((b) => b.top)), bottom: Math.max(...bs.map((b) => b.bottom)), width: 1, height: 1 }; } boxes[s] = r; if (r.right > W + 2 || r.left < -2) out.push(names[s] + ' runs off the side (' + Math.round(r.left) + ' to ' + Math.round(r.right) + ' of ' + W + ')'); if (r.top > H - 20 && W > 1000) out.push(names[s] + ' starts below the screen'); }
    if (W <= 1000) { const main = boxes['#play'] || boxes['#panel'], re = document.querySelector('#rail'), rail = re && vis(re); if (main && main.top > H - 120) out.push('on a phone the main card starts at ' + Math.round(main.top) + ' px, below the first screen (' + H + ')'); if (main && rail && rail.top < main.top) out.push('on a phone the view controls come before the main card'); }
    const pairs = [['#prog', '#decks'], ['#prog', '#navwrap'], ['#panel', '#rail'], ['#play', '#rail'], ['#leftcol', '#rail'], ['#panel', '#side'], ['#play', '#side'], ['#play', '#panel'], ['#navwrap', '#decks'], ['#panel', '#decks'], ['#play', '#decks'], ['#mri2d', '#play'], ['#mri2d', '#panel']];
    for (const [a, b] of pairs) { const A = boxes[a], B = boxes[b]; if (!A || !B) continue; const w = Math.min(A.right, B.right) - Math.max(A.left, B.left), h = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top); if (w > 6 && h > 6) out.push(names[a] + ' overlaps ' + names[b] + ' by ' + Math.round(w) + ' x ' + Math.round(h) + ' px'); }
    if (W > 1000) { const L = boxes['#leftcol'] || boxes['#panel'], Rr = boxes['#rail']; if (L && Rr && Rr.left - L.right < 200) out.push('only ' + Math.round(Rr.left - L.right) + ' px between the text panel and the controls for the brain'); }
    const cut = new Set(); document.querySelectorAll('button, .pill, h1, h2, h3, .ptitle').forEach((e) => { const r = vis(e); if (!r) return; if (e.scrollWidth > e.clientWidth + 3 && getComputedStyle(e).overflow !== 'visible') cut.add(e.innerText.trim().slice(0, 30)); if (r.right > W + 2 && r.left < W) cut.add('off right edge: ' + e.innerText.trim().slice(0, 30)); });
    if (cut.size) out.push('clipped text: ' + [...cut].slice(0, 6).join(' | '));
    const tiny = [...document.querySelectorAll('button')].filter((e) => { const r = vis(e); return r && (r.width < 28 || r.height < 22); }).map((e) => (e.innerText || e.id || e.title || '?').trim().slice(0, 16)); if (W < 500 && tiny.length) out.push('small tap targets: ' + [...new Set(tiny)].slice(0, 8).join(', '));
    return { out, ids: Object.keys(boxes).join(' ') }; };
  const states = [
    ['type', async (p) => { await p.evaluate(() => { gyrus.setMode('type'); gyrus.setDeck('areas'); gyrus.setSub('practice'); }); }],
    ['learn', async (p) => { await p.evaluate(() => { gyrus.setMode('learn'); }); }],
    ['explore', async (p) => { await p.evaluate(() => { gyrus.setMode('explore'); gyrus.select('hippocampus'); }); }],
    ['explore+cut', async (p) => { await p.evaluate(() => { gyrus.setMode('explore'); gyrus.select('thalamus'); }); await p.click('[data-axis="coronal"]').catch(() => {}); }],
    ['find', async (p) => { await p.evaluate(() => { const b = document.querySelector('[data-axis][aria-pressed="true"]'); if (b) b.click(); gyrus.setMode('find'); }); }],
    ['quiz', async (p) => { await p.evaluate(() => { gyrus.setMode('quiz'); }); }],
    ['paths list', async (p) => { await p.evaluate(() => { gyrus.setMode('paths'); }); }],
    ['paths tour', async (p) => { await p.evaluate(() => { gyrus.setMode('paths'); gyrus.startPath('consciousness'); gyrus.pathGo(0); gyrus.pathGo(6); }); }],
    ['paths direct', async (p) => { await p.evaluate(() => { gyrus.startPath('direct'); gyrus.pathGo(0); }); }],
  ];
  for (const [w, h] of sizes) {
    const p = await open(browser, w, h);
    for (const [name, fn] of states) {
      where = w + 'x' + h + ' ' + name;
      try { await fn(p); } catch (e) { issue('could not set up: ' + e.message.split('\n')[0]); continue; }
      await sleep(1100);
      const r = await p.evaluate(lay); checks++; r.out.forEach((x) => issue(x));
      if ((w === 390 || w === 1280 || w === 820 || w === 940 || w === 1024 || w === 1010) && ['type', 'explore', 'paths tour', 'explore+cut', 'paths list'].includes(name)) await p.screenshot({ path: path.join(SHOTS, 'qa_' + w + '_' + name.replace(/\W+/g, '_') + '.png') });
      if (name === 'type' && w === 1440) notes.push('visible blocks: ' + r.ids);
      if (w === 1440 && ['type', 'explore', 'paths tour'].includes(name)) { const a11y = await p.evaluate(() => { const v = (e) => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.width > 2 && r.height > 2 && cs.display !== 'none' && cs.visibility !== 'hidden'; }; const nameless = [...document.querySelectorAll('button')].filter((e) => v(e) && !(e.innerText || '').trim() && !e.getAttribute('aria-label') && !e.title).map((e) => e.id || e.className || e.outerHTML.slice(0, 40)); const imgs = [...document.querySelectorAll('img')].filter((e) => v(e) && !e.alt).length; const inputs = [...document.querySelectorAll('input')].filter((e) => v(e) && !e.getAttribute('aria-label') && !e.title && !(e.id && document.querySelector('label[for=' + e.id + ']')) && !(e.closest('[title]'))).map((e) => e.id); return { nameless, imgs, inputs, lang: document.documentElement.lang, title: document.title }; }); if (a11y.nameless.length) issue('buttons with no text, label or title: ' + [...new Set(a11y.nameless)].join(', ')); if (a11y.imgs) issue(a11y.imgs + ' images with no alt text'); if (a11y.inputs.length) issue('inputs with no label: ' + a11y.inputs.join(', ')); if (!a11y.lang) issue('the page does not declare its language'); if (name === 'type') notes.push('page title "' + a11y.title + '", language "' + a11y.lang + '"'); }
    }
    await p.context().close();
  }
}

// ---------------------------------------------------------------------------------------------- find, every region
const SCAN = (step) => `(x) => { const rc = document.querySelector('#gl').getBoundingClientRect(); const hits = []; for (let y = rc.top + 12; y < rc.bottom - 12; y += ${step}) for (let xx = rc.left + 12; xx < rc.right - 12; xx += ${step}) { const el = document.elementFromPoint(xx, y); if (!el || el.id !== 'gl') continue; const h = gyrus.pickAt(xx, y); const R0 = gyrus.R.get(x); if (h && ((h.type === 'deep' && R0.meshSet && R0.meshSet.has(h.mesh)) || (h.region && h.region.id === x))) hits.push([xx, y]); } return hits.length ? hits[Math.floor(hits.length / 2)] : null; }`;
async function locate(p, id, step) {
  for (const v of VIEWS) {
    await p.evaluate((vv) => gyrus.setView(vv), v); await sleep(680);
    const pt = await p.evaluate('(' + SCAN(step) + ')(' + JSON.stringify(id) + ')');
    if (pt) return pt;
  }
  return null;
}
async function partFind(browser) {
  const decks = (process.argv[3] || DECKS.join(',')).split(',');
  const p = await open(browser);
  await p.evaluate(() => gyrus.setMode('find')); await sleep(800);
  for (const deck of decks) {
    const ids = await p.evaluate((d) => [...gyrus.R.values()].filter((r) => r.deck === d).map((r) => r.id), deck);
    const hard = [], needInfl = []; let good = 0;
    const only = process.env.FIND_IDS ? process.env.FIND_IDS.split(',') : null;
    for (const id of ids) {
      if (only && !only.includes(id)) continue;
      where = 'find ' + deck + ' ' + id;
      await p.evaluate(([d, x]) => { window.__qaNext = x; gyrus.setDeck(d); }, [deck, id]); await sleep(600);
      const tgt = await p.evaluate(() => gyrus.Fd && gyrus.Fd.r && gyrus.Fd.r.id);
      if (!ok(tgt === id, 'could not make it the target (got ' + tgt + ')')) continue;
      const setInfl = (v) => p.evaluate((val) => { const e = document.querySelector('#inflate'); e.value = val; e.dispatchEvent(new Event('input', { bubbles: true })); }, v);
      let pt = await locate(p, id, 12), infl = false;
      if (!pt && ['deep', 'thalamus', 'brainstem'].includes(deck)) pt = await locate(p, id, 4); // very small structures need a finer scan
      if (!pt) { await setInfl(1); await sleep(1000); pt = await locate(p, id, 10); infl = !!pt; }
      if (!pt) { hard.push(id); await setInfl(0); await sleep(300); continue; }
      await sleep(450); pt = (await p.evaluate('(' + SCAN(infl ? 10 : 12) + ')(' + JSON.stringify(id) + ')')) || pt; // view has settled
      await p.mouse.click(pt[0], pt[1]); await sleep(450);
      if (infl) { needInfl.push(id); await setInfl(0); await sleep(300); }
      const right = await p.evaluate(() => (document.querySelector('#play').innerText.replace(/\s+/g, ' ').match(/(\d+) right/) || [0, -1])[1]);
      checks++; if (+right === 1) good++; else issue('clicking it was not counted as right');
    }
    notes.push('find ' + deck + ': ' + good + ' of ' + ids.length + ' clicked and counted' + (needInfl.length ? '; only reachable with the cortex inflated: ' + needInfl.join(', ') : '') + (hard.length ? '; not reachable at all from the six standard views: ' + hard.join(', ') : ''));
  }
  await p.context().close();
}

// ---------------------------------------------------------------------------------------------- hover
async function partHover(browser) {
  const p = await open(browser);
  const hoverCheck = async (label, ids, expectTip) => {
    for (const id of ids) {
      where = 'hover ' + label + ' ' + id;
      const pt = await locate(p, id, 14);
      if (!pt) { notes.push(label + ': ' + id + ' not on screen from the standard views'); continue; }
      await p.mouse.move(pt[0] - 40, pt[1] - 40); await sleep(120); await p.mouse.move(pt[0], pt[1], { steps: 4 }); await sleep(260);
      const s = await p.evaluate(() => ({ hov: gyrus.S.hover && gyrus.S.hover.id, tip: document.querySelector('#tip').classList.contains('on') ? document.querySelector('#tip').innerText : '' }));
      ok(s.hov === id, 'hovering it highlights ' + (s.hov || 'nothing'));
      if (expectTip) ok(s.tip.toLowerCase().includes(id.split('_')[0]), 'tooltip shows "' + s.tip + '"');
    }
  };
  const lobes = ['frontal_lobe', 'parietal_lobe', 'temporal_lobe', 'occipital_lobe', 'limbic_lobe'];
  for (let round = 0; round < 3; round++) { // results screen of a 10-item round, whichever lobe was asked last
    await p.evaluate(() => { gyrus.setMode('type'); gyrus.setDeck('lobes'); gyrus.setSub('practice'); }); await sleep(500);
    await p.click('[data-plen="10"]'); await sleep(500); let last = null;
    for (let i = 0; i < 12; i++) { const s = await tstate(p); if (!s.id) break; last = s.id; await typeName(p, s.name); const nx = await waitAdvance(p, s.id); if (!nx || nx.end) break; }
    await sleep(900); notes.push('round ' + (round + 1) + ' ended on ' + last);
    await hoverCheck('results screen (last asked ' + last + ')', lobes, true);
  }
  await p.evaluate(() => { const b = document.querySelector('[data-plen="endless"]') || document.querySelector('[data-plen="0"]'); if (b) b.click(); }); await sleep(300);
  for (const m of ['explore', 'learn']) { await p.evaluate((mm) => { gyrus.setMode(mm); gyrus.setDeck('lobes'); }, m); await sleep(700); const sel = await p.evaluate(() => gyrus.S.sel && gyrus.S.sel.id); await hoverCheck(m, lobes.filter((x) => x !== sel), true); }
  await p.evaluate(() => { gyrus.setMode('quiz'); gyrus.setDeck('lobes'); }); await sleep(800);
  await hoverCheck('quiz (the answer must highlight like the rest)', lobes, false);
  where = 'quiz name in question'; let tried = false; // a name given in the question is not accepted as the answer
  for (let k = 0; k < 14 && !tried; k++) {
    await p.evaluate(() => { window.__qaNext = 'frontopolar_cortex'; gyrus.setDeck('areas'); }); await sleep(500);
    const q = await p.evaluate(() => document.querySelector('#clue').innerText); if (!/area 10/i.test(q)) continue; tried = true;
    await typeName(p, 'area 10'); await sleep(900); ok(!(await p.evaluate(() => gyrus.T.done)), 'typing a name from the question ("area 10") was accepted');
    await p.keyboard.press('Enter'); await sleep(400); const st = await p.evaluate(() => document.querySelector('#play').innerText.replace(/\s+/g, ' ').match(/(\d+) missed/)); ok(st && +st[1] === 0, 'a name from the question was counted as a miss');
    for (let i = 0; i < 8; i++) await p.keyboard.press('Backspace'); await typeName(p, 'frontopolar cortex'); await sleep(700); ok(await p.evaluate(() => gyrus.T.done), 'the proper name was not accepted after that');
  }
  if (!tried) notes.push('quiz name-in-question: the Brodmann area 10 question did not come up in 14 draws');
  await p.context().close();
}

(async () => {
  const browser = await chromium.launch({ executablePath: EXE, args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const t0 = Date.now();
  try { await ({ explore: partExplore, type: partType, modes: partModes, paths: partPaths, misc: partMisc, layout: partLayout, find: partFind, hover: partHover })[part](browser); }
  catch (e) { issue('the test run itself stopped: ' + e.message.split('\n')[0]); }
  await browser.close();
  fs.writeFileSync(path.join(SHOTS, 'qa_' + part + (process.argv[3] ? '_' + process.argv[3].replace(/\W+/g, '-') : '') + '.json'), JSON.stringify({ part, checks, seconds: Math.round((Date.now() - t0) / 1000), issues, notes }, null, 1));
  const by = {}; issues.forEach((i) => { const k = i.what.replace(/"[^"]*"/g, '"…"').replace(/\d+/g, 'N').slice(0, 70); (by[k] = by[k] || []).push(i); });
  console.log(part + ': ' + checks + ' checks, ' + issues.length + ' issues, ' + Math.round((Date.now() - t0) / 1000) + ' s');
  Object.entries(by).sort((a, b) => b[1].length - a[1].length).slice(0, 40).forEach(([k, v]) => console.log('  ' + String(v.length).padStart(3) + ' x ' + v[0].what.slice(0, 150) + '   [' + v.slice(0, 3).map((x) => x.where).join('; ') + (v.length > 3 ? '; …' : '') + ']'));
  notes.forEach((n) => console.log('  note: ' + n.slice(0, 220)));
})();
