const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),expected=JSON.parse(fs.readFileSync(path.join(__dirname,'efficiency_expected.json')));
(async()=>{const b=await chromium.launch({headless:true,channel:'chrome'});try{
const p=await b.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[];
p.on('pageerror',e=>errors.push(e.message));await p.goto(process.env.DEMO_URL||pathToFileURL(path.join(root,'index.html')).href);
const cells=async key=>p.locator(`[data-efficiency-row="${key}"] td`).allTextContents();
const overflow=async()=>assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
const start=async k=>{await p.locator(`[data-budget="${k}"]`).click();await p.locator('#start-analysis').click();await p.locator('#reveal-results').waitFor();};
const reset=async()=>{await p.locator('[data-step="0"]').click();await p.locator('#start-analysis').waitFor();};
assert.equal(await p.locator('.efficiency-panel').count(),0);
for(let k=1;k<=5;k++){
 await start(k);assert.equal(await p.locator('[data-truth]').count(),0);
 assert.deepEqual(await cells('ligands'),['18 种',`${k} 种`,`${k} 种`]);
 assert.deepEqual(await cells('points'),['720 点',`${k*40} 点`,`${k*40} 点`]);
 assert.deepEqual(await cells('time'),['9.0 工时',`${(k*.5).toFixed(1)} 工时`,`${(k*.5).toFixed(1)} 工时`]);
 assert.deepEqual(await cells('hit'),Array(3).fill('揭晓后显示'));
 if(k===3){await p.locator('.efficiency-panel').screenshot({path:path.join(__dirname,'efficiency-before.png')});}
 await p.locator('#reveal-results').click();await p.locator('#show-comparison').waitFor();
 assert.deepEqual(await cells('hit'),['all','random','ai'].map(m=>(expected[k][m+'_hit']*100).toFixed(1)+'%'));
 assert.deepEqual(await cells('best'),['all','random','ai'].map(m=>expected[k][m+'_best'].toFixed(3)));
 if(k===3){await p.locator('.efficiency-panel').screenshot({path:path.join(__dirname,'efficiency-after.png')});}
 await reset();assert.equal(await p.locator('.efficiency-panel').count(),0);
}
await start(3);
await p.locator('#estimate-cost').fill('150');await p.locator('#estimate-minutes').fill('45');
const nums=arr=>arr.map(s=>Number(s.replace(/[^\d.]/g,'')));
assert.deepEqual(nums(await cells('cost')),[2700,450,450]);
assert.deepEqual(await cells('time'),['13.5 工时','2.3 工时','2.3 工时']);
assert.equal(await p.locator('[data-truth]').count(),0);
await p.locator('#reveal-results').click();await p.locator('#show-comparison').waitFor();
assert.equal(await p.locator('#estimate-cost').inputValue(),'150');
assert.deepEqual(nums(await cells('cost')),[2700,450,450]);
await p.locator('#estimate-cost').fill('');assert(await p.locator('.estimate-error').isVisible());assert.equal(await p.locator('#estimate-cost').getAttribute('aria-invalid'),'true');
await p.locator('#estimate-cost').fill('-1');assert(await p.locator('.estimate-error').isVisible());
await p.locator('#estimate-cost').fill('0');await p.locator('#estimate-minutes').fill('0');assert.deepEqual(nums(await cells('cost')),[0,0,0]);assert.deepEqual(await cells('time'),Array(3).fill('0.0 工时'));
await p.locator('#estimate-cost').fill('1000001');assert(await p.locator('.estimate-error').isVisible());
await p.locator('#estimate-cost').fill('100');await p.locator('#estimate-minutes').fill('30');
await p.locator('[data-step="1"]').click();assert.equal(await p.locator('[data-truth]').count(),0);assert.deepEqual(await cells('hit'),Array(3).fill('揭晓后显示'));
await p.locator('#reveal-results').click();await p.locator('#show-comparison').waitFor();
await p.setViewportSize({width:390,height:844});await overflow();await p.locator('.efficiency-panel').screenshot({path:path.join(__dirname,'efficiency-mobile.png')});
for (const cell of await p.locator('[data-efficiency-row="hit"] td').all()) { const box=await cell.boundingBox();assert(box.x>=0&&box.x+box.width<=390); }
await p.setViewportSize({width:320,height:700});await overflow();
await p.locator('#show-comparison').click();assert.equal(await p.locator('[data-summary="equal_rank"] td').nth(1).textContent(),'0.0818');assert.deepEqual(errors,[]);
const receipt={pass:true,budgets_checked:[1,2,3,4,5],reference:'exhaustive subset enumeration across all 15 pools',predicted_state_hides_oracles:true,estimate_input_edges_pass:true,estimates_persist_on_reveal:true,mobile_page_overflow:false,mobile_all_three_columns_visible:true,full_flow_pass:true,new_model_fits:0,errors};
fs.writeFileSync(path.join(__dirname,'efficiency_verification.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
