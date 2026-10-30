/* Shared presentation preferences. Scientific data and stored project records are unchanged. */
(() => {
'use strict';
const root=document.documentElement, media=matchMedia('(prefers-color-scheme: dark)');
const read=k=>{try{return localStorage.getItem(k)}catch{return null}},write=(k,v)=>{try{localStorage.setItem(k,v)}catch{}};
let theme=read('amadeus-theme')|| (media.matches?'dark':'light');
let language=read('amadeus-language')==='en'?'en':'zh';
const records=new WeakMap(),attributes=new WeakMap(),cache=new Map();let matcher=null,observer=null,queued=false;
const han=/[\u3400-\u9fff]/;
function translate(source){
 if(language!=='en'||!han.test(source))return source;
 const dict=window.AMADEUS_EN||{};
 if(dict[source])return dict[source];
 if(cache.has(source))return cache.get(source);
 const leading=source.match(/^\s*/)[0],trailing=source.match(/\s*$/)[0],text=source.trim();
 if(dict[text])return leading+dict[text]+trailing;
 let result=text.replace(/第\s*(\d+)\s*轮/g,'Round $1').replace(/(\d+)\s*\/\s*6\s*阶段/g,'$1 / 6 stages').replace(/(\d+)\s*个项目/g,'$1 projects').replace(/(\d+)\s*条历史记录/g,'$1 historical records').replace(/(\d+)\s*条候选/g,'$1 candidates').replace(/(\d+)\s*种候选配体/g,'$1 candidate ligands');
 if(!matcher){const keys=Object.keys(dict).filter(k=>k.length>=2&&k.length<=100).sort((a,b)=>b.length-a.length);matcher=new RegExp(keys.map(k=>k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|'),'g');}
 result=result.replace(matcher,key=>dict[key]);
 result=leading+result+trailing;cache.set(source,result);return result;
}
function setRoot(){root.dataset.theme=theme;root.lang=language==='en'?'en':'zh-CN';root.style.colorScheme=theme;}
setRoot();
function controls(){
 let bar=document.querySelector('.amadeus-preferences');
 if(!bar){bar=document.createElement('div');bar.className='amadeus-preferences';bar.setAttribute('role','group');bar.innerHTML='<button type="button" data-preference="language"></button><button type="button" data-preference="theme"></button>';
 }
 const host=document.querySelector('.top .round,.top-nav,.top-actions,.header-actions,.topbar-actions')||document.querySelector('.topbar,.top,header');
 if(host){bar.classList.remove('preferences-standalone');if(bar.parentElement!==host)host.append(bar)}else{bar.classList.add('preferences-standalone');if(!bar.isConnected)document.body.prepend(bar)}
 bar.setAttribute('aria-label',language==='en'?'Language and appearance':'语言与外观');
 const lang=bar.querySelector('[data-preference="language"]'),mode=bar.querySelector('[data-preference="theme"]');
 lang.textContent=language==='en'?'中文':'EN';lang.lang=language==='en'?'zh-CN':'en';lang.setAttribute('aria-label',language==='en'?'切换到中文':'Switch to English');lang.title=lang.getAttribute('aria-label');
 const label=language==='en'?(theme==='dark'?'Switch to light mode':'Switch to dark mode'):(theme==='dark'?'切换浅色模式':'切换深色模式');
 mode.title=label;mode.setAttribute('aria-label',label);mode.setAttribute('aria-pressed',String(theme==='dark'));
 mode.innerHTML=theme==='dark'?'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>':'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.1A8.5 8.5 0 0 1 9.9 4a8.5 8.5 0 1 0 10.1 10.1Z"/></svg>';
}
const skip=el=>el.closest('script,style,code,textarea,input,.message.user p:not(.demo-prompt),[data-user-content],[contenteditable="true"],.amadeus-preferences')||(el.closest('pre')&&!el.closest('button'));
function apply(){
 if(!document.body)return;
 if(observer)observer.disconnect();setRoot();controls();
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node;
 while((node=walker.nextNode())){
  if(!node.parentElement||skip(node.parentElement))continue;
  const previous=records.get(node),source=previous&&node.nodeValue===previous.last?previous.source:node.nodeValue;
  let value=translate(source);
  if(language==='en'&&value!==source&&node.parentElement.namespaceURI!=='http://www.w3.org/2000/svg'){
   if(node.previousSibling&&!/^\s|^[.,:;!?%)]/.test(value))value=' '+value;
   if(node.nextSibling&&!/\s$/.test(value))value+=' ';
  }
  if(node.nodeValue!==value)node.nodeValue=value;
  records.set(node,{source,last:value});
 }
 for(const el of document.querySelectorAll('[placeholder],[title],[aria-label],[alt]')){
  if(el.closest('.amadeus-preferences,[data-user-content]'))continue;
  const store=attributes.get(el)||{};
  for(const key of ['placeholder','title','aria-label','alt'])if(el.hasAttribute(key)){
   const current=el.getAttribute(key),old=store[key],source=old&&current===old.last?old.source:current,value=translate(source);
   if(current!==value)el.setAttribute(key,value);store[key]={source,last:value};
  }attributes.set(el,store);
 }
 const title=root.dataset.originalTitle||(root.dataset.originalTitle=document.title);document.title=translate(title);
 if(observer)observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label','alt']});
}
function schedule(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;apply()})}
function setLanguage(value){language=value==='en'?'en':'zh';write('amadeus-language',language);cache.clear();apply();document.dispatchEvent(new CustomEvent('amadeus:preferences',{detail:{language,theme}}));}
function setTheme(value){theme=value==='dark'?'dark':'light';write('amadeus-theme',theme);apply();}
window.AmadeusUI={get language(){return language},get theme(){return theme},translate,apply,setLanguage,setTheme};
document.addEventListener('click',e=>{const button=e.target.closest('[data-preference]');if(!button)return;if(button.dataset.preference==='language')setLanguage(language==='en'?'zh':'en');else setTheme(theme==='dark'?'light':'dark');});
media.addEventListener('change',e=>{if(!read('amadeus-theme')){theme=e.matches?'dark':'light';apply()}});
window.addEventListener('storage',e=>{if(['amadeus-theme','amadeus-language'].includes(e.key)){theme=read('amadeus-theme')||(media.matches?'dark':'light');language=read('amadeus-language')==='en'?'en':'zh';apply()}});
function boot(){observer=new MutationObserver(schedule);apply()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
