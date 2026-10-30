"""Build the review page from saved results. No fitting or API calls."""
import csv
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'amadeus/web'
read = lambda p: json.loads((ROOT / p).read_text())
concrete = read('results/engine-upgrade/result.json')
cv = read('results/engine-upgrade/verification.json')
oracle = read('amadeus/examples/concrete/oracle.json')
candidates = {c['id']: c for c in concrete['candidates']}
rows = [{**candidates[i], 'measured': oracle[i]} for i in concrete['order']]
source_paths = [
 'results/engine-upgrade/result.json','results/engine-upgrade/verification.json',
 'results/engine-upgrade/run_config.json','results/engine-upgrade/split_manifest.json',
 'results/engine-upgrade/oof_predictions.json','amadeus/examples/concrete/oracle.json',
 'amadeus/examples/concrete/provenance.json','results/reference/REPORT.md',
 'results/steels-case/verification.json','results/unprepared-20261029/independent_checks.json',
 'results/unprepared-20261029/README.md','docs/ENGINE_UPGRADE_RESULTS.md',
 'docs/STEELS_CASE.md','docs/NEW_RESEARCH_CASES.md',
 'docs/evidence/research-records.md','docs/evidence/research-excerpts.md','docs/evidence/sciencepal-results.md',
 'docs/evidence/sciencepal-check.json',
 'amadeus/data_engine.py','amadeus/engine.py','amadeus/workflow.py','amadeus/provider.py',
]
data = {'date':'2026-10-30','concrete': {'scores':concrete['scores'],'rows':rows,'verification':cv,
 'seconds':concrete['seconds'],'training':concrete['training_count']},
 'sources':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in source_paths]}
(WEB/'evidence-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
template=(ROOT/'docs/evidence/page-template.html').read_text()
# The data is bundled as well as downloadable so the page works directly from disk.
template=template.replace('/* EVIDENCE_DATA */',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
(WEB/'evidence.html').write_text(template)
print('Built evidence.html from',len(source_paths),'source files; no training.')
