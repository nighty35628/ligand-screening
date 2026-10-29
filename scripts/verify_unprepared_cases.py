"""Frozen, randomly selected unfamiliar datasets through the existing workflow.

This is an evaluation adapter, not a new application preset or model mechanism.
Run prepare first, then run each selected case. No holdout-dependent tuning.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import shutil
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from rdkit import Chem
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/unprepared-20261029'
SUMMARY = ROOT / 'results/unprepared-20261029'
DESCRIPTORS = ['element_count', 'mixing_entropy', 'mean_atomic_number',
               'std_atomic_number', 'mean_atomic_mass', 'mean_covalent_radius',
               'mean_outer_electrons']
CASES = {
    'double_perovskites_gap': {
        'title': '随机抽测 · 双钙钛矿带隙', 'label': 'gap gllbsc',
        'target': 'band_gap_ev', 'unit': 'eV',
        'goal': '根据元素组成及晶格位点元素筛选宽带隙双钙钛矿候选',
        'label_origin': 'GLLB-SC electronic-structure calculations; not experimental measurements',
        'context': ['a_1', 'b_1', 'a_2', 'b_2'],
    },
    'citrine_thermal_conductivity': {
        'title': '随机抽测 · 材料热导率', 'label': 'k_expt',
        'target': 'thermal_conductivity', 'unit': 'W/(m K)',
        'goal': '根据元素组成与记录的测试温度筛选高热导率材料条件',
        'label_origin': 'Published experimental thermal conductivity measurements',
        'context': ['temperature_k', 'temperature_kind'],
    },
}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def composition(formula):
    tokens = re.findall(r'([A-Z][a-z]?)([0-9]*\.?[0-9]*)', formula)
    if ''.join(e+n for e, n in tokens) != formula:
        raise ValueError('Unsupported formula: ' + formula)
    amounts = defaultdict(float)
    for e, n in tokens:
        amounts[e] += float(n or 1)
    total = sum(amounts.values())
    fractions = {e: v/total for e, v in amounts.items() if v > 0}
    identity = tuple((e, round(v, 12)) for e, v in sorted(fractions.items()))
    return fractions, hashlib.sha256(repr(identity).encode()).hexdigest()[:16]


def prepare(name):
    cfg = CASES[name]
    folder = BASE/name
    metadata = json.loads((BASE/'dataset_metadata.json').read_text())[name]
    raw = (folder/'raw.json.gz').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == metadata['hash']
    source = json.loads(gzip.decompress(raw))
    parsed, exclusions = [], []
    for i, values in enumerate(source['data']):
        record = dict(zip(source['columns'], values))
        y = record[cfg['label']]
        if y is None or not math.isfinite(float(y)):
            exclusions.append({'row': i, 'reason': 'missing or nonfinite target'})
            continue
        fractions, group = composition(record['formula'])
        if name == 'citrine_thermal_conductivity':
            assert record['k-units'] in {'W/m.K', 'W/m$\\cdot$K',
                'Wm$^{-1}$K$^{-1}$', 'W\\m K', 'W/mK'}
            condition = str(record['k_condition']).strip().lower()
            if record['k_condition_units'] == 'K':
                context = {'temperature_k': float(condition), 'temperature_kind': 'explicit_kelvin'}
            else:
                assert condition in ('room temperature', 'standard')
                context = {'temperature_k': '', 'temperature_kind': condition}
        else:
            context = {k: record[k] for k in cfg['context']}
        parsed.append({'raw_row': i, 'formula': record['formula'], 'fractions': fractions,
                       'composition_group': group, 'context': context, 'target': float(y)})
    elements = sorted({e for r in parsed for e in r['fractions']})
    fraction_columns = ['fraction_'+e for e in elements]
    table = Chem.GetPeriodicTable()
    grouped = defaultdict(list)
    for record in parsed:
        key = (record['composition_group'], tuple(record['context'].items()))
        grouped[key].append(record)
    rows, aggregates = [], []
    for records in grouped.values():
        r = records[0]
        f = r['fractions']
        z = sum(v*table.GetAtomicNumber(e) for e, v in f.items())
        row = {'id': name+'_'+str(r['raw_row']), 'composition_group': r['composition_group'],
               'formula': r['formula'], **{'fraction_'+e: f.get(e, 0) for e in elements},
               'element_count': len(f), 'mixing_entropy': -sum(v*math.log(v) for v in f.values()),
               'mean_atomic_number': z,
               'std_atomic_number': math.sqrt(sum(v*(table.GetAtomicNumber(e)-z)**2 for e, v in f.items())),
               'mean_atomic_mass': sum(v*table.GetAtomicWeight(e) for e, v in f.items()),
               'mean_covalent_radius': sum(v*table.GetRcovalent(e) for e, v in f.items()),
               'mean_outer_electrons': sum(v*table.GetNOuterElecs(e) for e, v in f.items()),
               **r['context'], cfg['target']: float(np.median([x['target'] for x in records]))}
        rows.append(row)
        if len(records) > 1:
            aggregates.append({'id': row['id'], 'raw_rows': [x['raw_row'] for x in records],
                               'values': [x['target'] for x in records], 'median': row[cfg['target']]})
    train, future = next(GroupShuffleSplit(n_splits=1, test_size=.15, random_state=42).split(
        rows, groups=[r['composition_group'] for r in rows]))
    assert not {rows[i]['composition_group'] for i in train}&{rows[i]['composition_group'] for i in future}
    features = fraction_columns+DESCRIPTORS+cfg['context']
    for kind, indices in [('training', train), ('candidates', future)]:
        columns = ['id', 'composition_group', 'formula']+features
        if kind == 'training':
            columns += [cfg['target']]
        with (folder/(kind+'.csv')).open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows[i] for i in indices)
    dump(folder/'oracle.json', {rows[i]['id']: rows[i][cfg['target']] for i in future})
    mapping = {'target': cfg['target'], 'id': 'id', 'group': 'composition_group',
               'task': 'regression', 'direction': 'max', 'unit': cfg['unit'], 'features': features,
               'feature_groups': {'element_fraction': fraction_columns+cfg['context'],
                                  'chemistry_descriptor': DESCRIPTORS+cfg['context']},
               'optimize': True, 'search_trials': 4, 'selection_metric': 'mae'}
    dump(folder/'mapping.json', mapping)
    audit = {'dataset': name, 'source': metadata, 'label_origin': cfg['label_origin'],
             'raw_rows': len(source['data']), 'usable_rows': len(rows), 'exclusions': exclusions,
             'duplicate_policy': 'Median target for identical normalized composition and recorded context; all records and values retained in this audit. No target threshold filtering.',
             'aggregates': aggregates, 'train_rows': len(train), 'candidate_rows': len(future),
             'train_groups': len({rows[i]['composition_group'] for i in train}),
             'candidate_groups': len({rows[i]['composition_group'] for i in future}),
             'group_overlap': 0, 'feature_count': len(features),
             'temperature_policy': 'Exact numeric temperatures only when units are Kelvin; room/standard remain categorical with numeric temperature missing. No assumed conversion.'}
    dump(folder/'audit.json', audit)
    print(name, {k: audit[k] for k in ('raw_rows', 'usable_rows', 'train_rows', 'candidate_rows', 'feature_count')}, flush=True)


def random_best(values, k):
    values = sorted(values)
    n = len(values)
    return sum(value*math.comb(i, k-1)/math.comb(n, k) for i, value in enumerate(values) if i >= k-1)


def run(name):
    from amadeus import workflow, server
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from scipy.stats import spearmanr
    folder = BASE/name
    output = SUMMARY/name
    output.mkdir(parents=True, exist_ok=True)
    assert not (output/'verification.json').exists(), 'Do not rerun completed holdout evaluation.'
    cfg = CASES[name]
    mapping = json.loads((folder/'mapping.json').read_text())
    audit = json.loads((folder/'audit.json').read_text())
    workflow.init(server, recover=False)
    previous = json.loads((folder/'project.json').read_text()) if (folder/'project.json').exists() else None
    p = workflow.load(previous['project_id']) if previous else workflow.create({'title': cfg['title'], 'goal': cfg['goal']})
    reuse_analysis = bool(p.get('analysis'))
    workflow.CANCEL[p['id']] = threading.Event()
    if not reuse_analysis:
        for kind in ('training', 'candidates'):
            workflow.upload(p, kind, (folder/(kind+'.csv')).read_text(), name+'-'+kind+'.csv')
    p['mapping'] = mapping
    p['sources'] = [{'id': workflow.uid(), 'title': name, 'url': audit['source']['url'],
                     'summary': audit['source']['description']}]
    p['research_context'] = {'material': cfg['title'], 'goal': cfg['goal'], 'source': audit['source'],
                             'evaluation': 'random unfamiliar dataset, no built-in preset'}
    p['operation'] = {'status': 'running', 'message': '随机新数据测试'}
    workflow.save(p)
    dump(folder/'project.json', {'project_id': p['id']})
    print(name, 'project', p['id'], 'finalizing saved predictions' if reuse_analysis else 'training started', flush=True)
    start = time.monotonic()
    try:
        if not reuse_analysis:
            workflow.train_table(p)
        analysis = p['analysis']
        training_folder = ROOT/Path(analysis['model_path']).parent
        # Seal recommendations and the exact final model before opening held-out labels.
        if (output/'sealed_predictions.json').exists():
            sealed = json.loads((output/'sealed_predictions.json').read_text())
            assert sealed['candidates'] == analysis['candidates']
            selected = sealed['selected']
        else:
            selected = p['selected'][:]
            dump(output/'sealed_predictions.json', {'model': analysis['model'], 'selected': selected,
                                                   'candidates': analysis['candidates']})
        oracle = json.loads((folder/'oracle.json').read_text())
        ys = np.array([oracle[c['id']] for c in analysis['candidates']])
        predictions = np.array([c['prediction'] for c in analysis['candidates']])
        training_y = np.array([float(r[mapping['target']]) for r in p['datasets']['training']['rows']])
        known = workflow.candidate_map(p)
        screening = {}
        for k in (1, 3, 5):
            ids = analysis['order'][:k]
            best = max(oracle[i] for i in ids)
            screening[str(k)] = {'selected_ids': ids, 'selected_best': best, 'pool_best': float(max(ys)),
                                  'regret': float(max(ys)-best), 'random_expected_best': random_best(ys, k),
                                  'unique_compositions': len({known[i]['features']['composition_group'] for i in ids}),
                                  'top_decile_hits': int(sum(oracle[i] >= np.quantile(ys, .9) for i in ids))}
        if p['round'] == 1:
            workflow.save_plan(p, notes='预先冻结配置的随机新数据验证；标签来源：'+cfg['label_origin'])
            workflow.record(p, [{'candidate_id': i, 'value': oracle[i], 'unit': cfg['unit'],
                                  'status': 'completed', 'note': cfg['label_origin']} for i in selected],
                            source=cfg['label_origin'])
            workflow.next_round(p)
        assert not set(selected)&set(p['selected'])
        p['operation'] = {'status': 'complete', 'message': '陌生数据闭环测试已完成'}
        workflow.save(p)
        reopened = workflow.load(p['id'])
        assert reopened['analysis']['id'] == analysis['id']
        (output/'report.html').write_bytes(workflow.export_report(reopened))
        summary = {'case': name, 'project_id': p['id'], 'model': analysis['model'],
                   'training_count': analysis['training_count'], 'candidate_count': len(ys),
                   'cv_mae': next(x['score'] for x in analysis['scores'] if x['model'] == analysis['model']),
                   'holdout_mae': float(mean_absolute_error(ys, predictions)),
                   'holdout_rmse': float(math.sqrt(mean_squared_error(ys, predictions))),
                   'holdout_r2': float(r2_score(ys, predictions)),
                   'holdout_spearman': float(spearmanr(ys, predictions).statistic),
                   'mean_baseline_mae': float(mean_absolute_error(ys, np.full(len(ys), training_y.mean()))),
                   'median_baseline_mae': float(mean_absolute_error(ys, np.full(len(ys), np.median(training_y)))),
                   'target_range': [float(ys.min()), float(ys.max())], 'unit': cfg['unit'],
                   'screening': screening, 'finalization_seconds': round(time.monotonic()-start, 2),
                   'reused_completed_training': reuse_analysis,
                   'engine_seconds': analysis['seconds'], 'model_configurations': len(analysis['scores']),
                   'round': p['round'], 'recorded': len(p['measurements']),
                   'dataset_versions': len(p['dataset_versions']), 'label_origin': cfg['label_origin'],
                   'engine_code_sha256': hashlib.sha256((ROOT/'amadeus/engine.py').read_bytes()).hexdigest(),
                   'model_sha256': hashlib.sha256((training_folder/'model.joblib').read_bytes()).hexdigest()}
        dump(output/'verification.json', summary)
        for filename in ('run_config.json', 'split_manifest.json', 'result.json', 'oof_predictions.json'):
            shutil.copyfile(training_folder/filename, output/filename)
        for filename in ('audit.json', 'mapping.json'):
            shutil.copyfile(folder/filename, output/filename)
        shutil.copyfile(BASE/'protocol.json', SUMMARY/'protocol.json')
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    except Exception as error:
        p['operation'] = {'status': 'error', 'message': str(error)}
        workflow.save(p)
        dump(folder/'failure.json', {'error': str(error), 'project_id': p['id']})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('case', nargs='?')
    args = parser.parse_args()
    if not (BASE/'protocol.json').exists():
        BASE.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SUMMARY/'protocol.json', BASE/'protocol.json')
    protocol = json.loads((BASE/'protocol.json').read_text())
    if args.action == 'prepare':
        if not (BASE/'dataset_metadata.json').exists():
            dump(BASE/'dataset_metadata.json', {name: json.loads((SUMMARY/name/'audit.json').read_text())['source'] for name in protocol['selected']})
        for name in protocol['selected']:
            raw_path = BASE/name/'raw.json.gz'
            if not raw_path.exists():
                metadata = json.loads((BASE/'dataset_metadata.json').read_text())[name]
                raw = urllib.request.urlopen(metadata['url'], timeout=60).read()
                assert hashlib.sha256(raw).hexdigest() == metadata['hash']
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(raw)
        protocol['preprocessing_policy'] = 'Use original recorded site elements or temperature context. Identical composition+context records aggregate by median, retaining all source rows. Composition groups never cross train/test.'
        protocol['screening_policy'] = 'Maximize gap for wide-gap oxide screening; maximize conductivity for heat transport. Budgets 1,3,5; compare exact random expected best. No outcome-dependent reconfiguration.'
        protocol['prepared_at_utc'] = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        dump(BASE/'protocol.json', protocol)
        for selected_case in protocol['selected']:
            prepare(selected_case)
    else:
        assert args.case in protocol['selected']
        run(args.case)
