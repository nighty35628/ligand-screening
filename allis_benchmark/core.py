from dataclasses import dataclass
from pathlib import Path
import hashlib
import time

import numpy as np
from scipy.stats import t
from sklearn.ensemble import RandomForestRegressor

from allis_delivery.core import (ASSETS as COMPONENT_ASSETS, Dataset, check_seal,
    pair_inputs, point_inputs, quality, read_json, require, select_columns, sha,
    validate_candidates)
from allis_delivery.evaluation import ranks, independent_midrank

ASSETS = Path(__file__).resolve().parent / 'assets'
METHODS = ('random', 'paired_RF', 'paired_RF_CI', 'paired_ET', 'direct_Q_ET', 'equal_rank')
NAMES = {'random':'随机选择', 'paired_RF':'成对 RF · 均值排序',
         'paired_RF_CI':'成对 RF · 上界排序', 'paired_ET':'成对 ET',
         'direct_Q_ET':'直接评分 ET', 'equal_rank':'等权排名融合'}


def protocol():
    check_seal(ASSETS, ASSETS / 'manifest.json')
    obj = read_json(ASSETS / 'protocol.json')
    require(obj['component_asset_manifest_sha256'] == sha(COMPONENT_ASSETS / 'manifest.json'), 'Component assets changed')
    return obj


@dataclass
class RFBundle:
    schema: int
    split: str
    columns: np.ndarray
    feature_names: list
    training_ids: list
    estimator: RandomForestRegressor
    reference_x: np.ndarray
    reference_y: np.ndarray


def fit_rf(data, split):
    cfg = protocol()['rf_folds'][split['id']]
    keep, _ = select_columns(data.features[:, :42], split['train'])
    require(keep.tolist() == cfg['columns'], 'RF training-only column filtering changed')
    x = point_inputs(data.features[split['train']][:, keep], data.dose[split['train']])
    y = data.responses(split['train']).ravel()
    pair_file = COMPONENT_ASSETS / 'data' / split['pairs_file']
    require(sha(pair_file) == cfg['pairs_sha256'], 'Training pair budget/indices changed')
    with np.load(pair_file, allow_pickle=False) as a:
        i, j = a['i'], a['j']
    target = y[i] - y[j]
    require(len(target) == 131072 and hashlib.sha256(target.tobytes()).hexdigest() == cfg['target_difference_sha256'], 'Training target drift')
    reg = RandomForestRegressor(**cfg['params']).fit(pair_inputs(x[i], x[j]), target)
    return RFBundle(1, split['id'], keep, data.feature_names,
                    [data.ids[k] for k in split['train']], reg, x, y)


def predict_rf(bundle, candidate):
    require(bundle.schema == 1, 'Unsupported RF model schema')
    x, dose, ids = validate_candidates(candidate, bundle.feature_names)
    require(not set(ids) & set(bundle.training_ids), 'Training/candidate identity overlap')
    query = point_inputs(x[:, bundle.columns], dose)
    ref = bundle.reference_x
    n = len(ref)
    batch = max(1, int(48 * 1024**2 / (n * ref.shape[1] * 3 * 4)))
    means, stds = [], []
    tree_error = 0.0
    for lo in range(0, len(query), batch):
        points = query[lo:lo + batch]
        pairs = pair_inputs(np.repeat(points, n, axis=0), np.tile(ref, (len(points), 1)))
        pred = bundle.estimator.predict(pairs)
        if lo == 0:
            manual = sum(tree.predict(pairs[:n]) for tree in bundle.estimator.estimators_) / len(bundle.estimator.estimators_)
            tree_error = float(np.max(abs(manual - pred[:n])))
            require(tree_error < 1e-10, 'Explicit tree prediction mismatch')
        values = pred.reshape(len(points), n) + bundle.reference_y[None, :]
        means.extend(values.mean(axis=1))
        stds.extend(values.std(axis=1, ddof=1))
    mean = np.asarray(means).reshape(len(ids), 40)
    sd = np.asarray(stds).reshape(len(ids), 40)
    ci = mean + t.ppf(.975, n - 1) * sd / np.sqrt(n)
    require(np.isfinite(mean).all() and np.isfinite(ci).all(), 'Invalid RF prediction')
    return {'ids':ids, 'rf_curves':mean.tolist(), 'rf_upper_curves':ci.tolist(),
            'rf_q':quality(mean).tolist(), 'rf_upper_q':quality(ci).tolist(),
            'dose_pmol':dose.tolist(), 'explicit_tree_max_error':tree_error}


def all_ranks(prediction):
    result = {k:v.tolist() for k,v in ranks(prediction['paired_q'], prediction['direct_q']).items()}
    result.update(random=[1.] * len(prediction['ids']),
                  paired_RF=independent_midrank(prediction['rf_q']),
                  paired_RF_CI=independent_midrank(prediction['rf_upper_q']))
    return {key:result[key] for key in METHODS}


def component_predictions(data, split):
    with np.load(COMPONENT_ASSETS / 'cache' / f"{split['id']}.npz", allow_pickle=False) as a:
        require(a['train'].tolist() == split['train'] and a['test'].tolist() == split['test'], 'Component cache identity mismatch')
        return {k:a[k].tolist() for k in ('paired_q', 'direct_q', 'paired_curves')}


def reference_rf(data, split):
    with np.load(ASSETS / 'cache' / f"{split['id']}.npz", allow_pickle=False) as a:
        require(a['train'].tolist() == split['train'] and a['test'].tolist() == split['test'], 'RF cache identity mismatch')
        return {'rf_curves':a['mean'].tolist(), 'rf_upper_curves':a['ci'].tolist(),
                'rf_q':a['qhat'].tolist(), 'rf_upper_q':a['qci'].tolist()}
