"""Offline checks for generated Wiki navigation, search, provenance and asset hashes."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib, json, runpy, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'amadeus/web';WIKI=WEB/'wiki'
class Document(HTMLParser):
 def __init__(self,text):super().__init__();self.ids=[];self.links=[];self.headings=0;self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag in ('a','link') and 'href' in a:self.links.append(a['href'])
  if tag in ('img','script') and 'src' in a:self.links.append(a['src'])
  if tag=='h1':self.headings+=1
pages=sorted(WIKI.rglob('*.html'));parsed={p:Document(p.read_text()) for p in pages};count=0
for p,d in parsed.items():
 assert d.headings==1,(p,'h1')
 assert len(d.ids)==len(set(d.ids)),(p,'duplicate ids')
 for href in d.links:
  u=urlsplit(href)
  if u.scheme or u.netloc:
   prefix='https://github.com/nighty35628/ligand-screening/blob/main/'
   if href.startswith(prefix):assert (ROOT/unquote(href[len(prefix):])).exists(),href
   continue
  target=(p.parent/unquote(u.path)).resolve() if u.path else p
  if target.is_dir():target=target/'index.html'
  assert target.is_relative_to(WEB.resolve()) and target.is_file(),(p,href)
  if u.fragment:
   td=parsed.get(target) or Document(target.read_text());assert unquote(u.fragment) in td.ids,(p,href)
  count+=1
search=json.loads((WIKI/'search-index.json').read_text())
for row in search:
 u=urlsplit(row['path']);p=WIKI/u.path/'index.html' if u.path else WIKI/'index.html'
 assert p in parsed,row
 if u.fragment:assert u.fragment in parsed[p].ids,row
assert any('128位' in row['text'] for row in search)
assert any('2048' in row['text'] for row in search)
assert len(pages)==len(runpy.run_path(str(ROOT/'docs/wiki/content.py'))['PAGES'])
for p,digest in json.loads((ROOT/'amadeus/web-manifest.json').read_text()).items():
 assert hashlib.sha256((WEB/p).read_bytes()).hexdigest()==digest,p
urls=ET.parse(WEB/'sitemap.xml').findall('{*}url');assert len(urls)==len(pages)+2
print(json.dumps({'pages':len(pages),'local_links_and_assets':count,'searchable_sections':len(search),'sitemap_urls':len(urls),'hashes':'pass'},ensure_ascii=False))
