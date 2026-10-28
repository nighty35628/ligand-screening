"""Audit the UI export against sealed existing outputs. Does not fit models."""
import hashlib,json,re,sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from allis_delivery.core import Dataset,check_seal,quality
P=ROOT/'demo';RUN=ROOT/'outputs/allis_retrain_verified'
read=lambda p:json.loads(p.read_text())
check_seal(RUN,RUN/'delivery_seal.json')
assert read(RUN/'verification.json')['pass']
data=read(P/'data.json');manifest=read(P/'manifest.json')
for name,digest in manifest['files'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest
assert manifest['source_delivery_seal_sha256']==hashlib.sha256((RUN/'delivery_seal.json').read_bytes()).hexdigest()
inline=json.loads(re.search(r'<script id="demo-data" type="application/json">(.*?)</script>',(P/'index.html').read_text(),re.S)[1])
assert inline==data
d=Dataset();truth=d.responses(range(90));gold=quality(truth)
assert len(data['molecules'])==90 and len(data['pools'])==15 and data['new_fits']==0
for i,m in enumerate(data['molecules']):
 assert m['id']==d.ids[i] and m['smiles']==d.molecules[i]['smiles']
 np.testing.assert_array_equal(m['gold_curve'],truth[i]);assert m['gold_Q']==gold[i]
 assert '<svg' in m['svg'] and '<script' not in m['svg']
metrics=read(RUN/'evaluation/metrics.json');rows={(r['split'],r['method']):r for r in metrics['rows'] if r['scope']=='all'}
for p,s in zip(data['pools'],d.splits):
 pred=read(RUN/'predictions'/f"{s['id']}.json")
 for key in ['train','test','paired_q','direct_q','ranks','paired_curves','dose_pmol']:assert p[key]==pred[key]
 assert p['id']==s['id'];np.testing.assert_array_equal(p['dose_pmol'],d.dose[p['test']])
 ra=rankdata(-np.array(p['paired_q']));rb=rankdata(-np.array(p['direct_q']))
 for method,ranks in [('paired_ET',ra),('direct_Q_ET',rb),('equal_rank',(ra+rb)/2)]:
  np.testing.assert_array_equal(p['ranks'][method],ranks)
  permutation=np.lexsort((np.random.default_rng(42).random(18),ranks)).tolist()
  assert p['orders'][method]==permutation
  for key,value in p['metrics'][method].items():assert value==rows[p['id'],method][key]
assert data['summary']==[s for s in metrics['summary'] if s['scope']=='all']
assert data['comparisons']==[s for s in metrics['comparisons'] if s['scope']=='all']
receipt={'pass':True,'source_seal_verified':True,'inline_payload_matches_export':True,'export_hashes_verified':True,'molecule_id_structure_truth_checks':90,'prediction_rank_selection_pool_checks':15,'summary_exact_match':True,'new_fits':0,'html_sha256':hashlib.sha256((P/'index.html').read_bytes()).hexdigest()}
(P/'qa/source_verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
