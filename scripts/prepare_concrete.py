import json,csv,hashlib
from pathlib import Path
import xlrd,numpy as np
from sklearn.model_selection import GroupShuffleSplit
root=Path('amadeus/examples/concrete');raw=(root/'Concrete_Data.xls').read_bytes()
book=xlrd.open_workbook(file_contents=raw);sheet=book.sheet_by_index(0);cols=['cement','slag','fly_ash','water','superplasticizer','coarse_aggregate','fine_aggregate','age_day','strength_mpa']
rows=[]
for i in range(1,sheet.nrows):
 vals=sheet.row_values(i);group=hashlib.sha256(repr(vals[:7]).encode()).hexdigest()[:16];rows.append({'id':f'concrete_{i:04d}','mix_group':group,**dict(zip(cols,vals))})
a,b=next(GroupShuffleSplit(n_splits=1,test_size=.15,random_state=42).split(rows,groups=[r['mix_group'] for r in rows]))
for name,indices,hide in [('training',a,False),('candidates',b,True)]:
 keys=['id','mix_group']+cols[:-1]+([] if hide else cols[-1:])
 with (root/f'{name}.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows[i] for i in indices)
(root/'oracle.json').write_text(json.dumps({rows[i]['id']:rows[i]['strength_mpa'] for i in b},indent=2))
cfg={'target':'strength_mpa','id':'id','group':'mix_group','task':'regression','direction':'max','unit':'MPa','features':cols[:-1],'feature_groups':{'composition':cols[:7],'condition':['age_day']},'optimize':True,'search_trials':4,'selection_metric':'mae'}
(root/'mapping.json').write_text(json.dumps(cfg,indent=2));(root/'provenance.json').write_text(json.dumps({'source':'https://archive.ics.uci.edu/dataset/165/concrete+compressive+strength','doi':'10.24432/C5PK67','author':'I-Cheng Yeh','license':'CC BY 4.0','raw_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows),'training':len(a),'candidates':len(b),'split':'15% composition-group holdout; age does not change group identity','note':'Engineering validation of materials workflow, not perovskite evidence.'},indent=2))
print(len(rows),len(a),len(b))
