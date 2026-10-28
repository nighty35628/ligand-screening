"""Independent exhaustive subset enumeration for the retrospective hit-rate display."""
from pathlib import Path
from itertools import combinations
import json, math
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data.json').read_text())
out={}
for k in range(1,6):
    total={'all_hit':1.0,'random_hit':0.0,'ai_hit':0.0,'all_best':0.0,'random_best':0.0,'ai_best':0.0}
    for p in d['pools']:
        y=[d['molecules'][i]['gold_Q'] for i in p['test']]
        best=max(y)
        good={i for i,v in enumerate(y) if abs(v-best)<1e-12}
        random_sets=list(combinations(range(len(y)),k))
        ranks=p['ranks']['equal_rank'];cut=sorted(ranks)[k-1]
        certain=tuple(i for i,r in enumerate(ranks) if r<cut)
        tied=[i for i,r in enumerate(ranks) if r==cut]
        ai_sets=[certain+c for c in combinations(tied,k-len(certain))]
        for method,sets in [('random',random_sets),('ai',ai_sets)]:
            hit=sum(bool(good.intersection(ids)) for ids in sets)/len(sets)
            q=math.fsum(max(y[i] for i in ids) for ids in sets)/len(sets)
            total[method+'_hit']+=hit/len(d['pools'])
            total[method+'_best']+=q/len(d['pools'])
            sealed=p['metrics']['random' if method=='random' else 'equal_rank']['B'+str(k)]
            assert abs(q-sealed)<1e-10,(p['id'],k,method,q,sealed)
        total['all_best']+=best/len(d['pools'])
    out[k]=total
(root/'qa/efficiency_expected.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
