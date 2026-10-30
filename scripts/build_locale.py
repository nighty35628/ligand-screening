"""Build the checked-in English UI catalogue. Translation is a development step only.

Run with --translate to translate new source strings using the locally configured
provider. The shipped application loads the generated catalogue without an API.
"""
from pathlib import Path
from html.parser import HTMLParser
import re,json,sys,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));WEB=ROOT/'amadeus/web'
strings=set()
def add(text):
 text=re.sub(r'\s+',' ',text).strip()
 if re.search('[\u3400-\u9fff]',text) and len(text)>1 and len(text)<4000:strings.add(text)
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('style','script','pre','code'):self.skip+=1
  if not self.skip:
   for k,v in attrs:
    if k in ('placeholder','aria-label','title','alt') and v:add(v)
 def handle_endtag(self,tag):
  if tag in ('style','script','pre','code'):self.skip=max(0,self.skip-1)
 def handle_data(self,text):
  if not self.skip:add(text)
for p in list((WEB/'wiki').rglob('*.html'))+[WEB/'index.html',WEB/'classic.html',WEB/'evidence.html']:
 parser=Text();parser.feed(p.read_text())
for p in [WEB/'workbench.js',WEB/'app.js',WEB/'demo-adapter.js',ROOT/'docs/wiki/wiki.js',*[ROOT/('amadeus/'+name+'.py') for name in ('workflow','data_engine','engine','provider','server','tabular')]]:
 s=p.read_text()
 for text in re.findall(r'[\u3400-\u9fff][^<>{}`\'"\\\n]*',s):
  text=text.rstrip(' :;,+)$[]=')
  if text:add(text)
for p in [WEB/'research-cases.json']:
 def walk(x):
  if isinstance(x,dict):
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
  elif isinstance(x,str):add(x)
 walk(json.loads(p.read_text()))
extra=ROOT/'docs/i18n/extra-zh.json'
if extra.exists():
 for text in json.loads(extra.read_text()):add(text)
source=ROOT/'docs/i18n/source-zh.json';source.write_text(json.dumps(sorted(strings),ensure_ascii=False,indent=2)+'\n')
target=ROOT/'docs/i18n/en.json';translations=json.loads(target.read_text()) if target.exists() else {}
missing=sorted(strings-translations.keys());print(f'{len(strings)} strings; {len(missing)} untranslated',flush=True)
if '--translate' in sys.argv and missing:
 from amadeus import provider
 chunks=[];chunk=[];size=0
 for s in missing:
  if size+len(s)>3800 or len(chunk)>=25:chunks.append(chunk);chunk=[];size=0
  chunk.append(s);size+=len(s)
 if chunk:chunks.append(chunk)
 def translate(chunk):
  from amadeus import provider
  payload={str(i):v for i,v in enumerate(chunk)}
  prompt='Translate every value of this JSON object into concise natural English for Amadeus, a materials research and modelling workbench. Return only a JSON object with the EXACT SAME KEYS (numeric strings) and translated string values. Preserve all numbers, units, formulas, IDs, variable names, code syntax, URLs and scientific claims exactly. Do not merge, omit or add entries. Fragments stay fragments. Use clear action labels. ET=Extra Trees, RF=Random Forest, 用量=amount, 配体=ligand, 实测=measured, 候选=candidate, 回顾性=retrospective, 配方=formulation, 指标=metric.\n'+json.dumps(payload,ensure_ascii=False)
  try:
   response=provider.request('/chat/completions',{'model':provider.settings().get('DEEPSEEK_MODEL','deepseek-flash'),'messages':[{'role':'user','content':prompt}],'thinking':{'type':'disabled'},'temperature':0.1,'max_tokens':12000})
   text=response['choices'][0]['message']['content'];obj=json.loads(text[text.find('{'):text.rfind('}')+1])
   if set(obj)!=set(payload) or any(not isinstance(v,str) for v in obj.values()):raise ValueError('Translation count/type mismatch')
   return {value:obj[key] for key,value in payload.items()}
  except (ValueError,KeyError):
   if len(chunk)==1:raise
   middle=len(chunk)//2
   return translate(chunk[:middle])|translate(chunk[middle:])
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  futures=[pool.submit(translate,c) for c in chunks]
  for i,f in enumerate(concurrent.futures.as_completed(futures)):
   translations.update(f.result());target.write_text(json.dumps(dict(sorted(translations.items())),ensure_ascii=False,indent=2)+'\n');print(f'Translated batch {i+1}/{len(chunks)}',flush=True)
if translations:
 translations.update({'你':'You','无':'None','否':'No','是':'Yes'})
 (WEB/'locale-en.js').write_text('/* Build-time English catalogue; no runtime translation API. */\nwindow.AMADEUS_EN='+json.dumps(translations,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n')
