"""Build a standalone presentation from already-verified results. Zero fits."""
from pathlib import Path
import sys,json,gzip,hashlib,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from allis_delivery.core import Dataset,read_json,check_seal,quality
from allis_delivery.evaluation import replay_selection
P=Path(__file__).resolve().parent;RUN=ROOT/'outputs/allis_retrain_verified'
if '--reuse-structures' in sys.argv:
 old_manifest=read_json(P/'manifest.json')
 assert hashlib.sha256((P/'data.json').read_bytes()).hexdigest()==old_manifest['files']['data.json']
 structures={m['id']:m for m in read_json(P/'data.json')['molecules']}
 rdkit_version=old_manifest['rdkit_version']
else:
 from rdkit import Chem
 from rdkit.Chem import rdMolDescriptors
 from rdkit.Chem.Draw import rdMolDraw2D
 structures=None;rdkit_version=Chem.rdBase.rdkitVersion
check_seal(RUN,RUN/'delivery_seal.json');require_receipt=read_json(RUN/'verification.json');assert require_receipt['pass']
d=Dataset();raw=json.loads(gzip.decompress((ROOT/'allis_delivery/assets/data/reaction_collection_train_AL0503.json.gz').read_bytes()));names={}
for row in raw['reactions']:
 if not row.get('ligand_solutions'):continue
 m=row['ligand_solutions'][0]['solute'];names[m['identifier']]={'name':m.get('name') or m.get('iupac_name') or m['smiles'],'label':m.get('int_label')}
truth=d.responses(range(90));gold=quality(truth);molecules=[]
for i,m in enumerate(d.molecules):
 if structures is not None:
  previous=structures[m['id']];assert previous['smiles']==m['smiles'];svg=previous['svg'];formula=previous['formula']
 else:
  mol=Chem.MolFromSmiles(m['smiles']);assert mol is not None
  drawer=rdMolDraw2D.MolDraw2DSVG(240,150);opt=drawer.drawOptions();opt.clearBackground=False;opt.bondLineWidth=1.5;opt.minFontSize=12;opt.maxFontSize=18
  drawer.DrawMolecule(mol);drawer.FinishDrawing();svg=drawer.GetDrawingText();svg=svg[svg.index('<svg'):];svg=re.sub(r"width=['\"]240px['\"]",'width="100%"',svg);svg=re.sub(r"height=['\"]150px['\"]",'height="100%"',svg);formula=rdMolDescriptors.CalcMolFormula(mol)
 assert 'viewBox' in svg and '<script' not in svg
 info=names[m['id']];molecules.append({'index':i,'id':m['id'],'name':info['name'],'label':f"L{info['label']:05d}" if isinstance(info['label'],int) else f"C{i+1:03d}",'smiles':m['smiles'],'formula':formula,'head_types':m['head_types'],'svg':svg,'gold_curve':truth[i].tolist(),'gold_Q':float(gold[i])})
metrics=read_json(RUN/'evaluation/metrics.json');idx={(r['split'],r['method']):r for r in metrics['rows'] if r['scope']=='all'};pools=[]
for split in d.splits:
 pred=read_json(RUN/'predictions'/f"{split['id']}.json");orders={method:replay_selection(pred['ranks'][method],18,42).tolist() for method in pred['ranks']}
 pools.append({'id':split['id'],'replicate':split['replicate'],'fold':split['fold'],'train':split['train'],'test':split['test'],'paired_q':pred['paired_q'],'direct_q':pred['direct_q'],'ranks':pred['ranks'],'orders':orders,'paired_curves':pred['paired_curves'],'dose_pmol':pred['dose_pmol'],'metrics':{method:{key:idx[split['id'],method][key] for key in ['AUR','B1','B2','B3','B4','B5','curve','oracle_Q']} for method in pred['ranks']}})
payload={'schema':1,'source':'verified_fixed_results','new_fits':0,'tie_seed':42,'default_pool':'r0_f0','default_budget':3,'molecules':molecules,'pools':pools,'summary':[r for r in metrics['summary'] if r['scope']=='all'],'comparisons':[r for r in metrics['comparisons'] if r['scope']=='all'],'metadata':{'unique_ligands':90,'doses_per_ligand':40,'training_per_pool':36,'candidate_per_pool':18,'retrospective':True,'mode':'静态演示：揭晓前只在界面隐藏既有答案','model_input_dose':'linear_pmol'}}
js=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
(P/'data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
template=(P/'template.html').read_text();html=template.replace('/*__STYLE__*/',(P/'style.css').read_text()).replace('/*__DATA__*/',js).replace('/*__APP__*/',(P/'app.js').read_text());assert '/*__' not in html
(P/'index.html').write_text(html)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(P/'manifest.json').write_text(json.dumps({'new_fits':0,'source_run':str(RUN.relative_to(ROOT)),'source_delivery_seal_sha256':sha(RUN/'delivery_seal.json'),'source_verification_sha256':sha(RUN/'verification.json'),'rdkit_version':rdkit_version,'pool_count':15,'molecule_count':90,'files':{f.name:sha(f) for f in [P/'index.html',P/'data.json',P/'template.html',P/'style.css',P/'app.js',P/'build_demo.py']}},indent=2)+'\n')
print(json.dumps({'standalone_html':str(P/'index.html'),'bytes':(P/'index.html').stat().st_size,'pools':len(pools),'molecules':len(molecules),'new_fits':0}))
