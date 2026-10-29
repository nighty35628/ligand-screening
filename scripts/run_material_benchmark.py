import json
from pathlib import Path
from amadeus.tabular import parse_csv,fit
root=Path('amadeus/examples/concrete');folder=Path('outputs/engine-concrete-20261029');folder.mkdir(parents=True,exist_ok=True)
payload={'training':parse_csv((root/'training.csv').read_text()),'candidates':parse_csv((root/'candidates.csv').read_text()),'mapping':json.loads((root/'mapping.json').read_text())}
(folder/'input.json').write_text(json.dumps(payload));result=fit(payload,folder);print(result['model'],result['seconds']);print([(s['model'],round(s['score'],3)) for s in result['scores']])
