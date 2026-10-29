"""Package the two completed runs for browser playback. Never trains a model."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from amadeus.tabular import parse_csv
from amadeus.data_engine import audit

def build():
    web=ROOT/'amadeus/web'
    cases=json.loads((web/'research-cases.json').read_text())
    for name in ('double_perovskites_gap','citrine_thermal_conductivity'):
        cfg=cases[name];src=ROOT/'amadeus/examples'/name;res=ROOT/'results/unprepared-20261029'/name
        result=json.loads((res/'result.json').read_text());sealed=json.loads((res/'sealed_predictions.json').read_text())
        assert result['candidates']==sealed['candidates']
        mapping=json.loads((src/'mapping.json').read_text());datasets={};versions=[]
        for kind in ('training','candidates'):
            ds=parse_csv((src/f'{kind}.csv').read_text());ds.update(id=f'public-{name}-{kind}',filename=f'{name}-{kind}.csv')
            if kind=='candidates':assert mapping['target'] not in ds['columns']
            versions.append(dict(id=ds['id'],kind=kind,reason=cfg['title']+' · 公开数据整理',audit=audit(ds)))
            datasets[kind]={k:v for k,v in ds.items() if k!='rows'}|dict(count=len(ds['rows']),preview=ds['rows'][:5])
        result.update(id=f'public-{name}-frozen',data_id=datasets['training']['id'],source=cfg['source_title']+' · '+cfg['label'],replay=True)
        fixture=dict(analysis=result,datasets=datasets,mapping=mapping,provenance=json.loads((src/'provenance.json').read_text()),oracle=json.loads((src/'oracle.json').read_text()),versions=versions,verification=json.loads((res/'verification.json').read_text()))
        (web/cfg['snapshot']).write_text(json.dumps(fixture,ensure_ascii=False,separators=(',',':'))+'\n')
        print(name,'packaged unchanged predictions',len(result['candidates']))
if __name__=='__main__':build()
