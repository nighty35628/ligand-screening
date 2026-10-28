"""Rebuild the standalone page from unchanged frozen data and current UI sources."""
from pathlib import Path
import hashlib
import json

root=Path(__file__).resolve().parents[1]/'demo/final'
manifest=json.loads((root/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'data.json')==manifest['files']['data.json'], 'Frozen research data changed'
data=json.loads((root/'data.json').read_text())
js=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
html=(root/'template.html').read_text().replace('/*__STYLE__*/',(root/'style.css').read_text()).replace('/*__DATA__*/',js).replace('/*__APP__*/',(root/'app.js').read_text())
assert '/*__' not in html
(root/'index.html').write_text(html)
manifest['files']={name:sha(root/name) for name in manifest['files']}
manifest['ui_flow']='setup_analysis_recommendation_measurement_comparison'
manifest['data_changed_by_ui_redesign']=False
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'html':str(root/'index.html'),'unchanged_data_sha256':sha(root/'data.json'),'html_sha256':sha(root/'index.html')}))
