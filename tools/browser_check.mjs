#!/usr/bin/env node
// Headless functional test of a rendered guide (QA Auditor / Experience Designer).
//   node tools/browser_check.mjs jobs/<id>/guide.html [--shots jobs/<id>/screens]
// Checks: no console/page errors, every tab renders, route switching works,
// the level input highlights a row, progress persists, mobile width has no
// horizontal scroll. Prints PASS/FAIL lines; exit 1 on any FAIL.
import { createRequire } from 'module';
import path from 'path';
import fs from 'fs';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { console.log('SKIP playwright not installed'); process.exit(0); }

const file = process.argv[2];
const si = process.argv.indexOf('--shots');
const shots = si > 0 ? process.argv[si + 1] : null;
if (!file) { console.error('usage: node tools/browser_check.mjs <guide.html> [--shots dir]'); process.exit(2); }
const url = 'file://' + path.resolve(file);
let fails = 0;
const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fails++; };

const browser = await chromium.launch();
for (const [name, vp] of [['desktop', { width: 1280, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
  const page = await browser.newPage({ viewport: vp, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.googleapis|net::ERR/.test(m.text())) errors.push(m.text()); });
  await page.goto(url, { waitUntil: 'load' });
  ok(errors.length === 0, `${name}: no script errors ${errors.join(' | ')}`);
  ok(await page.locator('#title').innerText() !== '', `${name}: title rendered`);
  const tabs = await page.locator('[data-tab]').evaluateAll(b => b.map(x => x.dataset.tab));
  for (const t of tabs) {
    await page.click(`[data-tab="${t}"]`);
    const txt = await page.locator(`#p-${t}`).innerText();
    ok(txt.trim().length > 20, `${name}: tab ${t} renders content`);
  }
  if (name === 'desktop') {
    await page.click('[data-tab="route"]');
    const routes = await page.locator('[data-route]').evaluateAll(b => b.map(x => x.dataset.route));
    for (const r of routes) {
      await page.click(`[data-route="${r}"]`);
      ok(await page.locator('article.card').count() > 0, `route ${r}: step cards render`);
    }
    const mid = await page.evaluate(() => { const g = JSON.parse(document.getElementById('guide-data').textContent);
      return Math.floor((g.meta.from_level + g.meta.to_level) / 2); });
    await page.fill('#mylvl', String(mid));
    await page.click('[data-tab="levels"]');
    ok(await page.locator('tr.cur').count() === 1, 'level input highlights the current level row');
    await page.click('[data-tab="route"]');
    const first = page.locator('[data-done]').first();
    await first.check();
    await page.reload();
    ok(await page.locator('[data-done]').first().isChecked(), 'progress persists across reload');
    if (shots) { fs.mkdirSync(shots, { recursive: true }); await page.screenshot({ path: path.join(shots, 'desktop.png'), fullPage: false }); }
  } else {
    await page.click('[data-tab="route"]');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    ok(overflow <= 1, `mobile: no horizontal page scroll (overflow ${overflow}px)`);
    if (shots) await page.screenshot({ path: path.join(shots, 'mobile.png'), fullPage: false });
  }
  await page.close();
}
await browser.close();
console.log(fails ? `${fails} FAIL` : 'ALL PASS');
process.exit(fails ? 1 : 0);
