// Offline browser checks: existing results only, no model fits.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root=path.resolve(__dirname,'..');
const D=JSON.parse(fs.readFileSync(path.join(root,'data.json'),'utf8'));
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[],network=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  await page.goto(pathToFileURL(path.join(root,'index.html')).href);
  assert.equal(await page.locator('#pool-select option').count(),15);
  assert.equal(await page.locator('#pool-select').inputValue(),'r0_f0');
  assert.equal(await page.locator('#budget-select').inputValue(),'3');
  assert.equal(await page.locator('[data-truth]').count(),0);
  let checked=0;
  for(const p of D.pools){
   await page.selectOption('#pool-select',p.id);
   assert.equal(await page.locator('[data-truth]').count(),0);
   assert.equal(await page.locator('#candidate-rows tr').count(),18);
   const initial=p.orders.equal_rank[0];
   assert.equal(await page.locator('.detail h3').textContent(),D.molecules[p.test[initial]].name);
   assert((await page.locator('.model-paths').textContent()).includes(p.paired_q[initial].toFixed(3)));
   assert((await page.locator('.model-paths').textContent()).includes(p.direct_q[initial].toFixed(3)));
   for(let b=1;b<=5;b++){
    await page.selectOption('#budget-select',String(b));
    assert.equal(await page.locator('[data-truth]').count(),0);
    for(const method of ['paired_ET','direct_Q_ET','equal_rank']){
     const ids=await page.locator(`[data-method="${method}"] [data-selected]`).evaluateAll(els=>els.map(e=>Number(e.dataset.selected)));
     assert.deepEqual(ids,p.orders[method].slice(0,b).map(i=>p.test[i]));
    }
    await page.locator('#reveal-button').click();
    assert.equal(await page.locator('#candidate-rows [data-truth]').count(),18);
    const truthRows=await page.locator('#candidate-rows [data-truth]').allTextContents();
    assert.deepEqual(truthRows,p.orders.equal_rank.map(i=>D.molecules[p.test[i]].gold_Q.toFixed(3)));
    for(const method of ['paired_ET','direct_Q_ET','equal_rank']){
     const max=Math.max(...p.orders[method].slice(0,b).map(i=>D.molecules[p.test[i]].gold_Q));
     assert.equal(await page.locator(`[data-method="${method}"] .strategy-result strong`).textContent(),max.toFixed(3));
     assert((await page.locator(`[data-method="${method}"] .strategy-result small`).textContent()).includes(p.metrics[method].curve[b-1].toFixed(3)));
    }
    assert.equal(await page.locator('#prediction svg.chart polyline').count(),2);
    await page.locator('#reveal-button').click();
    assert.equal(await page.locator('[data-truth]').count(),0);
    checked++;
   }
  }
  await page.selectOption('#pool-select','r0_f0');await page.selectOption('#budget-select','3');
  await page.locator('#candidate-rows tr').last().locator('button').focus();
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('#candidate-rows button[aria-pressed="true"]:focus').count(),1);
  assert.equal(await page.locator('#prediction svg.chart polyline').count(),1);
  // Final confirmation screenshots, default first pool, not a result-selected pool.
  await page.selectOption('#pool-select','r0_f0');
  assert.equal(await page.locator('.table-scroll').evaluate(e=>e.scrollTop),0);
  await page.screenshot({path:path.join(__dirname,'desktop-hidden.png'),fullPage:true});
  await page.locator('#reveal-button').click();
  await page.screenshot({path:path.join(__dirname,'desktop-revealed.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:path.join(__dirname,'mobile-revealed.png'),fullPage:true});
  await page.locator('[data-method="equal_rank"] [data-pick]').first().click();
  assert.equal(await page.locator('#prediction:focus').count(),1);
  await page.selectOption('#budget-select','2');
  assert.equal(await page.locator('[data-truth]').count(),0);
  await page.locator('[data-reveal]').click();
  assert.equal(await page.locator('#candidate-rows [data-truth]').count(),18);
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  const receipt={pass:true,checked_pool_budget_states:checked,strategy_selections_checked:checked*3,source:'existing_fixed_results',new_fits:0,offline_file_protocol:true,external_network_requests:network.length,browser_errors:errors,desktop_viewport:[1440,1000],mobile_viewport:[390,844],mobile_page_overflow:false,keyboard_candidate_selection:true,hidden_on_pool_or_budget_change:true};
  fs.writeFileSync(path.join(__dirname,'browser_verification.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify(receipt));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
