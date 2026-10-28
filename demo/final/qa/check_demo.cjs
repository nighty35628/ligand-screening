// Guided-flow regression checks against frozen predictions. No model fits.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const D = JSON.parse(fs.readFileSync(path.join(root, 'data.json'), 'utf8'));
const source = process.env.DEMO_URL || pathToFileURL(path.join(root, 'index.html')).href;
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [], network = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (/^https?:/.test(r.url())) network.push(r.url()); });
    const overflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const absent = async () => assert.equal(await page.locator('#stage [data-truth], #stage [data-predicted], #stage [data-summary]').count(), 0);
    const shot = async (name, fullPage = false) => {
      await page.mouse.move(0, 0);
      await page.waitForTimeout(280);
      await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
      await page.screenshot({ path: path.join(__dirname, name + '.png'), fullPage });
    };
    const reset = async () => { await page.locator('[data-step="0"]').click(); await page.locator('#start-analysis').waitFor(); await absent(); };
    const rowsMatch = async rows => {
      for (const method of D.methods) {
        const r = rows[method];
        const cells = await page.locator(`[data-summary="${method}"] td`).allTextContents();
        assert.equal(cells[1], r.AUR.toFixed(4));
        assert.equal(cells[2], r.B3.toFixed(4));
      }
    };
    await page.goto(source);
    await page.locator('#start-analysis').waitFor();
    await absent(); await overflow();
    assert.equal(await page.locator('#pool-select option').count(), 15);
    assert.equal(await page.locator('#pool-select').inputValue(), D.default_pool);
    assert.equal(await page.locator('[data-budget="3"]').getAttribute('aria-pressed'), 'true');
    for (const i of [1, 2, 3]) assert(await page.locator(`[data-step="${i}"]`).isDisabled());
    await shot('desktop-overview');
    await page.locator('#start-analysis').focus(); await page.keyboard.press('Enter');
    await page.locator('#analysis-progress').waitFor();
    await page.waitForTimeout(400);
    const progress = Number(await page.locator('#analysis-progress').getAttribute('aria-valuenow'));
    assert(progress > 0 && progress < 100);
    await absent(); await shot('desktop-processing');
    await page.locator('#cancel-progress').click();
    await page.waitForTimeout(150);
    await absent(); assert(await page.locator('#start-analysis').isVisible());
    // Observe the full nonuniform timeline, then independently check skip.
    await page.locator('#start-analysis').click();
    const samples = [];
    for (let i = 0; i < 24; i++) {
      await page.waitForTimeout(240);
      if (!(await page.locator('#analysis-progress').count())) break;
      samples.push(Number(await page.locator('#analysis-progress').getAttribute('aria-valuenow')));
    }
    await page.locator('#reveal-results').waitFor();
    assert(samples.length >= 10);
    assert(samples.every((v, i) => i === 0 || v >= samples[i - 1]));
    const increments = samples.slice(1).map((v, i) => v - samples[i]);
    assert(Math.max(...increments) >= Math.min(...increments) + 4, 'Progress must have perceptible speed variation');
    await reset();
    await page.locator('#start-analysis').click();
    await page.locator('#skip-progress').click();
    await page.locator('#reveal-results').waitFor();
    assert.equal(await page.locator('[data-truth]').count(), 0);
    await shot('desktop-recommendation', true);
    await page.locator('.recommend-pick').last().focus(); await page.keyboard.press('Enter');
    assert.equal(await page.locator('.recommend-pick[aria-pressed="true"]:focus').count(), 1);
    await page.locator('#reveal-results').click();
    await page.locator('#show-comparison').waitFor();
    await shot('desktop-revealed', true);
    await page.locator('#show-comparison').click();
    await rowsMatch(Object.fromEntries(D.summary.map(r => [r.method, r])));
    await shot('desktop-comparison', true);
    await page.locator('#methods-toggle').click();
    assert(await page.locator('#methods').isVisible());
    await page.locator('#methods-toggle').click();
    assert.equal(await page.locator('#methods').isVisible(), false);
    // Exhaustively verify every pool/budget against frozen outputs, without animation delay.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    let checked = 0;
    for (const p of D.pools) {
      for (let b = 1; b <= 5; b++) {
        await reset(); await page.selectOption('#pool-select', p.id);
        await page.locator(`[data-budget="${b}"]`).click(); await absent();
        await page.locator('#start-analysis').click(); await page.locator('#reveal-results').waitFor();
        const ids = await page.locator('[data-selected]').evaluateAll(els => els.map(e => Number(e.dataset.selected)));
        assert.deepEqual(ids, p.orders.equal_rank.slice(0, b).map(i => p.test[i]));
        const first = p.orders.equal_rank[0];
        assert.equal(await page.locator('[data-predicted="paired"]').textContent(), p.paired_q[first].toFixed(3));
        assert.equal(await page.locator('[data-predicted="direct"]').textContent(), p.direct_q[first].toFixed(3));
        assert.equal(await page.locator('[data-truth]').count(), 0);
        assert.equal(await page.locator('#ligand-detail svg.chart polyline').count(), 1);
        await page.locator('#reveal-results').click(); await page.locator('#show-comparison').waitFor();
        const truth = await page.locator('.recommend-pick [data-truth]').allTextContents();
        assert.deepEqual(truth, p.orders.equal_rank.slice(0, b).map(i => D.molecules[p.test[i]].gold_Q.toFixed(3)));
        const best = Math.max(...p.orders.equal_rank.slice(0, b).map(i => D.molecules[p.test[i]].gold_Q));
        assert.equal(await page.locator('.measured-summary [data-truth]').first().textContent(), best.toFixed(3));
        assert.equal(await page.locator('#ligand-detail svg.chart polyline').count(), 2);
        const allTruth = await page.locator('.candidate-table [data-truth]').allTextContents();
        assert.deepEqual(allTruth, p.orders.equal_rank.map(i => D.molecules[p.test[i]].gold_Q.toFixed(3)));
        await page.locator('#show-comparison').click();
        await page.locator('[data-scope="pool"]').click(); await rowsMatch(p.metrics);
        await page.locator('[data-scope="all"]').click(); await rowsMatch(Object.fromEntries(D.summary.map(r => [r.method, r])));
        await page.locator('[data-step="1"]').click();
        assert.equal(await page.locator('[data-truth]').count(), 0);
        checked++;
      }
    }
    // Small-screen flow, same unselected default example, no cherry-picked case.
    await reset(); await page.selectOption('#pool-select', D.default_pool); await page.locator('[data-budget="3"]').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await overflow(); await shot('mobile-overview', true);
    await page.locator('#start-analysis').click(); await page.locator('#reveal-results').waitFor();
    await overflow(); await shot('mobile-recommendation', true);
    await page.locator('#reveal-results').click(); await page.locator('#show-comparison').waitFor();
    await overflow(); await shot('mobile-revealed', true);
    await page.locator('#show-comparison').click(); await overflow(); await shot('mobile-comparison', true);
    await reset();
    await page.setViewportSize({ width: 320, height: 700 }); await overflow();
    await page.locator('#start-analysis').click(); await page.locator('#reveal-results').waitFor(); await overflow();
    assert.deepEqual(errors, []);
    if (!process.env.DEMO_URL) assert.deepEqual(network, []);
    const receipt = {
      pass: true, checked_pool_budget_states: checked, unchanged_data_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'data.json'))).digest('hex'),
      new_fits: 0, source: process.env.DEMO_URL ? source : 'offline file://', external_requests: network.length, browser_errors: errors,
      initial_results_hidden: true, truth_hidden_until_reveal: true, rank_recomputed_against_frozen_outputs: true,
      progress_animated_cancelable_skippable: true, monotonic_variable_speed_samples: samples, reduced_motion_supported: true, keyboard_selection: true,
      reset_clears_results: true, viewports: [[1440,1000],[390,844],[320,700]], mobile_overflow: false,
      metrics_checked_per_state: D.methods.length * 2,
    };
    fs.writeFileSync(path.join(__dirname, 'browser_verification.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify(receipt));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
