"""Prepare a composition-only steel strength task from the public Matbench file."""
import gzip,json,re,hashlib,csv,math
from pathlib import Path
import numpy as np
from rdkit import Chem
from sklearn.model_selection import GroupShuffleSplit

def prepare():
    root=Path('amadeus/examples/steels');raw=(root/'raw.json.gz').read_bytes();data=json.loads(gzip.decompress(raw));table=Chem.GetPeriodicTable();parsed=[]
    for i,(formula,y) in enumerate(data['data']):
        tokens=re.findall(r'([A-Z][a-z]?)([0-9]*\.?[0-9]*)',formula)
        if ''.join(e+n for e,n in tokens)!=formula:raise ValueError('Unsupported formula: '+formula)
        amounts={}
        for e,n in tokens:amounts[e]=amounts.get(e,0)+float(n or 1)
        total=sum(amounts.values());frac={e:v/total for e,v in amounts.items()}
        canonical=tuple((e,round(v,12)) for e,v in sorted(frac.items()))
        parsed.append((formula,frac,hashlib.sha256(repr(canonical).encode()).hexdigest()[:16],float(y)))
    elements=sorted(set(e for _,f,_,_ in parsed for e in f));fraction_cols=['fraction_'+e for e in elements];descriptor_cols=['element_count','mixing_entropy','mean_atomic_number','std_atomic_number','mean_atomic_mass','mean_covalent_radius','mean_outer_electrons']
    rows=[]
    for i,(formula,frac,group,y) in enumerate(parsed):
        row={'id':f'steel_{data["index"][i]}','composition_group':group,'formula':formula,**{'fraction_'+e:frac.get(e,0) for e in elements}}
        meanz=sum(v*table.GetAtomicNumber(e) for e,v in frac.items())
        row.update(element_count=len(frac),mixing_entropy=-sum(v*math.log(v) for v in frac.values()),mean_atomic_number=meanz,std_atomic_number=math.sqrt(sum(v*(table.GetAtomicNumber(e)-meanz)**2 for e,v in frac.items())),mean_atomic_mass=sum(v*table.GetAtomicWeight(e) for e,v in frac.items()),mean_covalent_radius=sum(v*table.GetRcovalent(e) for e,v in frac.items()),mean_outer_electrons=sum(v*table.GetNOuterElecs(e) for e,v in frac.items()),yield_strength_mpa=y)
        rows.append(row)
    a,b=next(GroupShuffleSplit(n_splits=1,test_size=.15,random_state=42).split(rows,groups=[r['composition_group'] for r in rows]))
    assert not {rows[i]['composition_group'] for i in a}&{rows[i]['composition_group'] for i in b}
    for name,indices,hide in [('training',a,False),('candidates',b,True)]:
        cols=['id','composition_group','formula']+fraction_cols+descriptor_cols+([] if hide else ['yield_strength_mpa'])
        with (root/f'{name}.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows[i] for i in indices)
    (root/'oracle.json').write_text(json.dumps({rows[i]['id']:rows[i]['yield_strength_mpa'] for i in b},indent=2))
    (root/'mapping.json').write_text(json.dumps({'target':'yield_strength_mpa','id':'id','group':'composition_group','task':'regression','direction':'max','unit':'MPa','features':fraction_cols+descriptor_cols,'feature_groups':{'element_fraction':fraction_cols,'chemistry_descriptor':descriptor_cols},'optimize':True,'search_trials':4,'selection_metric':'mae'},indent=2))
    (root/'provenance.json').write_text(json.dumps({'source':'https://hackingmaterials.lbl.gov/automatminer/datasets.html','download':'https://ml.materialsproject.org/projects/matbench_steels.json.gz','original_source':'https://acdc.alcf.anl.gov/mdf/detail/steel_strength_v1.1/','original_doi':'10.18126/524z-vd6m','license':'CC BY 4.0 (original steel_strength data)','raw_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows),'unique_compositions':len({r['composition_group'] for r in rows}),'training':len(a),'candidates':len(b),'split':'15% normalized-composition group holdout, seed 42; not the official Matbench evaluation','features':'Normalized element amounts from composition plus explicit RDKit periodic-table summaries. No tensile strength, elongation or processing data used.'},indent=2))
    print(len(rows),len(a),len(b),'unique compositions',len({r['composition_group'] for r in rows}))
if __name__=='__main__':prepare()
