"""Export the verified unified comparison without RDKit or model fitting."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from allis_delivery.core import Dataset, check_seal, read_json, sha, write_json
from allis_delivery.evaluation import replay_selection
from allis_benchmark.core import METHODS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args();run=args.run_dir.resolve();out=ROOT/'demo/final';out.mkdir(exist_ok=True)
    check_seal(run,run/'delivery_seal.json')
    assert read_json(run/'verification.json')['pass']
    prior=read_json(ROOT/'demo/data.json');prior_manifest=read_json(ROOT/'demo/manifest.json')
    assert prior_manifest['files']['data.json']==sha(ROOT/'demo/data.json')
    data=Dataset();metrics=read_json(run/'evaluation/metrics.json')
    assert len(prior['molecules'])==90
    assert [m['id'] for m in prior['molecules']]==data.ids
    # Reuse existing chemically rendered SVGs, verify every reused ground truth against this run.
    idx={(r['split'],r['method']):r for r in metrics['rows']};pools=[]
    for s in data.splits:
        p=read_json(run/'predictions'/f"{s['id']}.json")
        for k,i in enumerate(s['test']):assert abs(prior['molecules'][i]['gold_Q']-idx[s['id'],'equal_rank']['gold_Q'][k])<1e-12
        p.update(replicate=s['replicate'],fold=s['fold'],id=s['id'],
                 orders={m:replay_selection(p['ranks'][m],18,42).tolist() for m in METHODS},
                 metrics={m:{k:idx[s['id'],m][k] for k in ('AUR','B1','B2','B3','B4','B5','curve','oracle_Q')} for m in METHODS})
        pools.append(p)
    payload={'schema':2,'source_run':str(run.relative_to(ROOT)),'methods':list(METHODS),'tie_seed':42,
             'default_pool':'r0_f0','default_budget':3,'molecules':prior['molecules'],'pools':pools,
             'summary':metrics['summary'],'comparisons':metrics['comparisons'],
             'execution':read_json(run/'execution.json'),'verification':read_json(run/'verification.json'),
             'static_replay':True,'new_blind_confirmation':False}
    js=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
    (out/'data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    html=(out/'template.html').read_text().replace('/*__STYLE__*/',(out/'style.css').read_text()).replace('/*__DATA__*/',js).replace('/*__APP__*/',(out/'app.js').read_text())
    assert '/*__' not in html
    (out/'index.html').write_text(html)
    manifest={'source_run':str(run.relative_to(ROOT)),'source_delivery_sha256':sha(run/'delivery_seal.json'),
              'structure_source':'demo/data.json','structure_source_sha256':sha(ROOT/'demo/data.json'),
              'export_new_fits':0,'files':{p.name:sha(p) for p in [out/'index.html',out/'data.json',out/'template.html',out/'style.css',out/'app.js']}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'path':str(out/'index.html'),'pools':len(pools),'methods':len(METHODS),'new_fits':0}))


if __name__=='__main__':main()
