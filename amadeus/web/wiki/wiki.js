'use strict';
const dialog=document.querySelector('#search-dialog'),input=document.querySelector('#search-input'),results=document.querySelector('#search-results'),status=document.querySelector('#search-status');
const base=document.body.dataset.wikiBase;
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function search(query){
 const q=query.trim().toLocaleLowerCase();
 if(!q){results.innerHTML='<p class="empty">搜索使用方法、模型、字段或案例，例如“分组”“ET”“API”。</p>';status.textContent='全文搜索 · 在浏览器本地完成';return;}
 const tokens=q.split(/\s+/).filter(Boolean),docs=window.AMADEUS_WIKI_SEARCH||[];
 const hits=docs.map(d=>{const title=d.title.toLowerCase(),section=d.section.toLowerCase(),text=d.text.toLowerCase();let score=0;for(const t of tokens){if(!(title+' '+section+' '+text).includes(t))return null;score+=(title.includes(t)?12:0)+(section.includes(t)?8:0)+(text.includes(t)?1:0);}return {...d,score};}).filter(Boolean).sort((a,b)=>b.score-a.score).slice(0,16);
 results.innerHTML=hits.length?hits.map(d=>{const pos=Math.max(0,d.text.toLowerCase().indexOf(tokens[0])-28),snippet=d.text.slice(pos,pos+130);return `<a href="${base+d.path}"><b>${escapeHtml(d.title)}${d.section?' · '+escapeHtml(d.section):''}</b><span>${pos?'…':''}${escapeHtml(snippet)}${pos+130<d.text.length?'…':''}</span></a>`;}).join(''):'<p class="empty">没有找到匹配内容。试试更短的关键词，例如“浓度”“分组”或模型名称。</p>';
 status.textContent=hits.length?`找到 ${hits.length}${hits.length===16?' 条以上':' 条'}相关章节 · ↑↓选择，Enter打开`:'没有匹配章节';
}
function openSearch(){if(!dialog.open)dialog.showModal();input.focus();search(input.value);}
document.querySelector('.search-open').addEventListener('click',openSearch);
document.querySelector('#search-close').addEventListener('click',()=>dialog.close());
input.addEventListener('input',()=>search(input.value));
dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
dialog.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();dialog.close();return;}if(e.key==='Enter'&&document.activeElement===input){const first=results.querySelector('a');if(first){e.preventDefault();first.click();}return;}if(!['ArrowDown','ArrowUp'].includes(e.key))return;const links=[...results.querySelectorAll('a')];if(!links.length)return;e.preventDefault();const i=links.indexOf(document.activeElement);links[(i+(e.key==='ArrowDown'?1:-1)+links.length)%links.length].focus();});
document.addEventListener('keydown',e=>{const editing=/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)||document.activeElement.isContentEditable;if((e.key.toLowerCase()==='k'&&(e.ctrlKey||e.metaKey))||(e.key==='/'&&!editing&&!dialog.open)){e.preventDefault();openSearch();}if(e.key==='Escape')closeMenu();});
const menu=document.querySelector('.menu-toggle');function closeMenu(){document.body.classList.remove('menu-open');menu.setAttribute('aria-expanded','false');}
menu.addEventListener('click',()=>{const open=document.body.classList.toggle('menu-open');menu.setAttribute('aria-expanded',String(open));});document.querySelector('.backdrop').addEventListener('click',closeMenu);
document.querySelectorAll('pre').forEach(pre=>{const button=document.createElement('button');button.className='copy';button.textContent='复制';button.setAttribute('aria-label','复制代码');pre.append(button);button.addEventListener('click',async()=>{const code=pre.querySelector('code').textContent;try{await navigator.clipboard.writeText(code);button.textContent='已复制';}catch{const range=document.createRange();range.selectNodeContents(pre.querySelector('code'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);button.textContent='已选中，请复制';}setTimeout(()=>button.textContent='复制',2000);});});
const toc=[...document.querySelectorAll('.toc a')];if('IntersectionObserver'in window){const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting)toc.forEach(a=>a.setAttribute('aria-current',String(a.hash==='#'+e.target.id)));},{rootMargin:'-12% 0px -65% 0px'});document.querySelectorAll('article h2').forEach(h=>observer.observe(h));}
