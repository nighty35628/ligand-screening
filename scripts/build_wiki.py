"""Generate the static Wiki with Python's standard library; no training or API calls."""
from pathlib import Path
from html import escape, unescape
from html.parser import HTMLParser
import hashlib, json, re, runpy
from collections import OrderedDict
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'docs/wiki'; WEB=ROOT/'amadeus/web'; OUT=WEB/'wiki'
PAGES=runpy.run_path(str(SRC/'content.py'))['PAGES']
BASE='https://nighty35628.github.io/ligand-screening/'
REPO='https://github.com/nighty35628/ligand-screening/blob/main/'
groups=OrderedDict()
for p in PAGES:groups.setdefault(p['group'],[]).append(p)
PAGES=[p for pages in groups.values() for p in pages]
class Plain(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,s):self.parts.append(s)
def plain(s):
 p=Plain();p.feed(s);return re.sub(r'\s+',' ',' '.join(p.parts)).strip()
search=[]
for index,p in enumerate(PAGES):
 slug=p['slug']; prefix='../' if slug else './';site='../../' if slug else '../';body=p['body'];toc=[]
 def heading(m):
  name=plain(m[1]);ident=f'section-{len(toc)+1}';toc.append((ident,name));return f'<h2 id="{ident}">{m[1]}<a class="anchor" href="#{ident}" aria-label="链接到{name}">#</a></h2>'
 body=re.sub(r'<h2>(.*?)</h2>',heading,body,flags=re.S)
 def wiki(m):return 'href="'+prefix+(m[1]+'/' if m[1] else '')+'"'
 body=re.sub(r'href="wiki:([^"]*)"',wiki,body)
 body=body.replace('href="site:','href="'+site)
 body=body.replace('<table>','<div class="table-scroll"><table>').replace('</table>','</table></div>')
 nav=''
 for group,pages in groups.items():
  nav+=f'<details open><summary>{escape(group)}</summary>'
  for a in pages:
   href=prefix+(a['slug']+'/' if a['slug'] else '')
   current=' aria-current="page"' if a['slug']==slug else ''
   nav+=f'<a href="{href}"{current}>{escape(a["title"])}</a>'
  nav+='</details>'
 toc_links=''.join(f'<a href="#{i}">{escape(t)}</a>' for i,t in toc)
 refs=''.join(f'<li><a href="{REPO+s}">{escape(s)}</a></li>' for s in p['sources'])
 for s in p['sources']:assert (ROOT/s).is_file(),s
 pager=''
 for offset,label,cls in [(-1,'上一篇','previous'),(1,'下一篇','next')]:
  n=index+offset
  if 0<=n<len(PAGES):
   a=PAGES[n];url=prefix+(a['slug']+'/' if a['slug'] else '')
   pager+=f'<a class="{cls}" href="{url}"><small>{label}</small>{escape(a["title"])}</a>'
 path=(slug+'/' if slug else '')
 # Every heading is indexed separately; search links directly to its section.
 sections=re.split(r'<h2 id="([^"]+)">',body)
 search.append({'title':p['title'],'section':'','text':p['description']+' '+plain(sections[0]),'path':path})
 for i in range(1,len(sections),2):
  ident=sections[i];fragment=sections[i+1];title,_,rest=fragment.partition('</h2>')
  search.append({'title':p['title'],'section':plain(re.sub(r'<a class="anchor".*?</a>','',title)),'text':plain(rest),'path':path+'#'+ident})
 content=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="{escape(p['description'],quote=True)}"><title>{escape(p['title'])} · Amadeus Wiki</title><link rel="canonical" href="{BASE}wiki/{path}"><link rel="icon" href="{site}mark.svg"><link rel="stylesheet" href="{prefix}wiki.css"><script defer src="{prefix}search-index.js"></script><script defer src="{prefix}wiki.js"></script></head>
<body data-wiki-base="{prefix}"><a class="skip" href="#content">跳到正文</a><header class="top"><a class="identity" href="{prefix}" aria-label="Amadeus Wiki 首页"><img src="{site}logo.svg" alt="Amadeus"><span>文档</span></a><nav class="top-nav" aria-label="站点导航"><button class="search-open" aria-haspopup="dialog" aria-controls="search-dialog"><span>搜索文档</span><kbd>⌘ K</kbd></button><a class="outside" href="{site}">体验工作台</a><a class="outside" href="{site}evidence.html">技术证据</a><a class="outside" href="https://github.com/nighty35628/ligand-screening">GitHub</a><button class="menu-toggle" aria-expanded="false" aria-controls="docs-nav">目录</button></nav></header><div class="backdrop"></div>
<div class="layout"><aside class="sidebar"><nav id="docs-nav" aria-label="文档目录">{nav}<a href="{site}">返回研究工作台</a><a href="{site}evidence.html">研发与技术证据</a></nav></aside><main class="content" id="content"><div class="breadcrumb"><a href="{prefix}">文档</a> / {escape(p['group'])}</div><h1>{escape(p['title'])}</h1><p class="description">{escape(p['description'])}</p><div class="meta">更新于 2026-10-30 · 对应当前仓库实现</div><details class="toc-mobile"><summary>本页目录</summary>{toc_links}</details><article>{body}<details class="refs"><summary>相关代码与资料</summary><ul>{refs}</ul></details></article><nav class="pager" aria-label="文档翻页">{pager}</nav><footer class="doc-footer"><span>Amadeus · To seek. To find. Together.</span><a href="{REPO}docs/wiki/content.py">查看文档源文件</a></footer></main><aside class="toc" aria-label="本页目录"><strong>本页目录</strong>{toc_links}</aside></div>
<dialog class="search-box" id="search-dialog" aria-label="搜索项目文档"><div class="search-head"><label class="visually-hidden" for="search-input">搜索关键词</label><input id="search-input" type="search" placeholder="搜索模型、数据、操作与案例…" autocomplete="off"><button id="search-close" aria-label="关闭搜索">Esc</button></div><div id="search-results" class="search-results"></div><div id="search-status" class="search-status" role="status" aria-live="polite">全文搜索 · 在浏览器本地完成</div></dialog></body></html>'''
 target=OUT/slug/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
for name in ['wiki.css','wiki.js']:(OUT/name).write_bytes((SRC/name).read_bytes())
(OUT/'search-index.js').write_text('window.AMADEUS_WIKI_SEARCH='+json.dumps(search,ensure_ascii=False).replace('</','<\\/')+';\n')
(OUT/'search-index.json').write_text(json.dumps(search,ensure_ascii=False,indent=2)+'\n')
urls=[BASE,BASE+'evidence.html']+[BASE+'wiki/'+(p['slug']+'/' if p['slug'] else '') for p in PAGES]
(WEB/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{escape(u)}</loc><lastmod>2026-10-30</lastmod></url>\n' for u in urls)+'</urlset>\n')
manifest={str(p.relative_to(WEB)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(WEB.rglob('*')) if p.is_file() and not p.name.startswith('.')}
(ROOT/'amadeus/web-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Built {len(PAGES)} Wiki pages, {len(search)} searchable sections, {len(urls)} sitemap URLs.')
