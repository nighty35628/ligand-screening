/* Browser checks for the shared appearance/language layer; no model training. */
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
let playwright;try{playwright=require('playwright')}catch{playwright=require('../outputs/wiki-preview/node_modules/playwright')}const {chromium}=playwright;
const out=path.resolve('outputs/preferences-check');fs.mkdirSync(out,{recursive:true});
const server=spawn('python3',['-m','http.server','8799','--bind','127.0.0.1'],{cwd:'amadeus/web',stdio:'ignore'});
const mode=process.argv[2]||'verify',han=/[\u3400-\u9fff]/;let extra=new Set();
(async()=>{let browser;try{
 browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1600,height:1050},colorScheme:'light'}),page=await context.newPage();let errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8799/?demo',{waitUntil:'networkidle'});
 async function collect(){for(const s of await page.evaluate(()=>{const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT),out=[];let n;while(n=w.nextNode()){if(!n.parentElement.closest('pre,code,script,style,textarea,.message.user')&&/[\u3400-\u9fff]/.test(n.nodeValue))out.push(n.nodeValue.trim());}for(const el of document.querySelectorAll('[placeholder],[title],[aria-label],[alt]'))for(const k of ['placeholder','title','aria-label','alt'])if(el.hasAttribute(k)&&/[\u3400-\u9fff]/.test(el.getAttribute(k)))out.push(el.getAttribute(k));return out}))if(s)extra.add(s);}
 await collect();
 const ids=await page.evaluate(()=>fetch('./research-cases.json').then(r=>r.json()).then(Object.keys));
 const samples=[];
 for(const id of [...ids.filter(id=>id!=='concrete'),'specialist','concrete']){
  await page.evaluate(()=>localStorage.removeItem('amadeus-online-projects-v1'));await page.reload({waitUntil:'networkidle'});
  const p=await page.evaluate(async id=>{const api=window.AmadeusDemo.api;let p=await api('/api/projects',{title:'Preference verification',goal:'Preserve my research input: CsPbBr3 40 nmol'});const base='/api/projects/'+p.id;
   async function act(action,args={}){p=await api(base+'/action',{action,args});while(p.operation.status==='running'){await new Promise(r=>setTimeout(r,50));p=await api(base);}if(p.operation.status==='failed')throw Error(p.operation.message);}
   if(id==='specialist')await act('specialist');else await act('material_example',{example:id,replay:true});await act('save_plan');await act('history_results');return p;
  },id);
  samples.push({id:p.id,case:id,analysis:JSON.stringify(p.analysis),task:JSON.stringify(p.task)});
  await page.goto('http://127.0.0.1:8799/?demo&check='+id+'#'+p.id,{waitUntil:'networkidle'});
  console.log('Case ready:',id);
  for(const view of ['overview','engine','evidence','data','plan','results','report']){await page.locator('[data-view="'+view+'"]').first().click();await collect();}
 }
 if(mode==='collect'){fs.writeFileSync('docs/i18n/extra-zh.json',JSON.stringify([...extra].sort(),null,2));console.log('Collected '+extra.size+' runtime strings from all five cases and views.');return;}
 await page.goto('http://127.0.0.1:8799/?demo#'+samples.at(-1).id,{waitUntil:'networkidle'});
 await page.locator('[data-preference="language"]').click();await page.waitForFunction(()=>document.documentElement.lang==='en');
 await page.locator('[data-preference="theme"]').click();await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
 extra.clear();const leftovers=[];
 for(const view of ['overview','engine','evidence','data','plan','results','report']){await page.locator('[data-view="'+view+'"]').first().click();await collect();if(view==='overview'){await page.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await page.screenshot({path:out+'/desktop-dark-en.png'});}if(view==='report'){await page.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await page.screenshot({path:out+'/report-dark-en.png'});}}
 const popupReady=page.waitForEvent('popup');await page.locator('a[href$="/report"]').first().click();const popup=await popupReady;await popup.waitForLoadState('networkidle');if(await popup.locator('html').getAttribute('lang')!=='en')throw Error('Report language did not persist');await popup.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await popup.screenshot({path:out+'/report-popup-dark-en.png'});await popup.emulateMedia({media:'print'});const printBackground=await popup.locator('body').evaluate(e=>getComputedStyle(e).backgroundColor);if(printBackground!=='rgb(255, 255, 255)')throw Error('Print background is not white');await popup.close();
 const after=await page.evaluate(id=>window.AmadeusDemo.api('/api/projects/'+id),samples.at(-1).id);if(JSON.stringify(after.analysis)!==samples.at(-1).analysis||JSON.stringify(after.task)!==samples.at(-1).task)throw Error('Language/theme changed scientific state');
 await page.reload({waitUntil:'networkidle'});if(await page.locator('html').getAttribute('lang')!=='en'||await page.locator('html').getAttribute('data-theme')!=='dark')throw Error('Preference persistence failed');
 await page.locator('[data-preference="language"]').click();await page.waitForFunction(()=>document.documentElement.lang==='zh-CN');await page.locator('[data-preference="language"]').click();
 await page.goto('http://127.0.0.1:8799/wiki/models/',{waitUntil:'networkidle'});await page.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await page.screenshot({path:out+'/wiki-dark-en.png'});await page.locator('.search-open').click();await page.locator('#search-input').fill('model');await page.waitForFunction(()=>document.querySelectorAll('#search-results a').length>0);await page.keyboard.press('Escape');
 await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:8799/?demo',{waitUntil:'networkidle'});await page.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await page.screenshot({path:out+'/mobile-dark-en.png',fullPage:true});const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));if(mobile.scroll>mobile.width+2)throw Error('Mobile horizontal overflow: '+JSON.stringify(mobile));
 await page.locator('[data-preference="theme"]').click();await page.locator('[data-preference="language"]').click();await page.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await page.screenshot({path:out+'/mobile-light-zh.png',fullPage:true});
 await page.setViewportSize({width:1600,height:1050});await page.goto('http://127.0.0.1:8799/?demo',{waitUntil:'networkidle'});await page.evaluate(()=>document.getAnimations().filter(a=>a.effect?.getTiming().iterations!==Infinity).forEach(a=>a.finish()));await page.screenshot({path:out+'/desktop-light-zh.png'});
 // Regression: language switches reformat dates, and long titles cannot squeeze row metadata.
 await page.evaluate(async()=>{for(const title of ['Concrete formulation screening','High-strength steel alloy candidates under different treatment conditions'])await window.AmadeusDemo.api('/api/projects',{title,goal:'Compare available historical records and experimental conditions.'});});
 await page.reload({waitUntil:'networkidle'});await page.locator('[data-preference="language"]').click();
 let dateRows=0;
 for(const width of [1440,768,390]){
  await page.setViewportSize({width,height:1050});
  const rows=await page.locator('.recent-row').evaluateAll(rows=>rows.map(row=>{const text=row.querySelector('.recent-summary').getBoundingClientRect(),meta=row.querySelector('.recent-meta').getBoundingClientRect();return {overlap:text.right>meta.left,day:row.querySelector('.ui-date-day').textContent,clock:row.querySelector('.ui-date-clock').textContent,wrapped:[...row.querySelectorAll('.recent-round,.ui-date-day,.ui-date-clock')].some(el=>el.getBoundingClientRect().height>parseFloat(getComputedStyle(el).lineHeight)+1)}}));
  if(rows.some(row=>row.overlap||row.wrapped||!/[A-Z][a-z]{2}/.test(row.day)||!/^\d{2}:\d{2}$/.test(row.clock)))throw Error('Date layout/locale regression: '+JSON.stringify({width,rows}));dateRows+=rows.length;
 }
 await page.locator('[data-preference="language"]').click();if(!await page.locator('.ui-date-day').first().innerText().then(text=>/\d{4}\/\d{2}\/\d{2}/.test(text)))throw Error('Chinese date format was not restored');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(out+'/remaining-zh.json',JSON.stringify([...extra].sort(),null,2));fs.writeFileSync(out+'/verification.json',JSON.stringify({five_case_views:35,scientific_state_unchanged:true,preference_persistence:true,language_roundtrip:true,english_wiki_search:true,date_layout_rows_checked:dateRows,date_language_roundtrip:true,mobile,page_errors:errors},null,2));console.log('Preferences browser verification passed.');
 }finally{if(browser)await browser.close();server.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
