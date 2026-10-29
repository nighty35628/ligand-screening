"""Small fixed-budget tabular workflow, executed in a cancellable subprocess."""
import csv
import io
import json
import math
import sys
from pathlib import Path


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    columns = reader.fieldnames or []
    if not columns or any(not c.strip() for c in columns) or len(set(columns)) != len(columns):
        raise ValueError('请使用带有唯一列名的 CSV 文件。')
    rows = list(reader)
    if not rows or any(None in row for row in rows):
        raise ValueError('CSV 没有数据，或某行的列数与表头不一致。')
    if len(rows) > 20000 or len(columns) > 300:
        raise ValueError('请先选择本轮需要的记录和特征，最多20000行、300列。')
    return {'columns': columns, 'rows': rows}


def fit(payload, directory):
    if payload['mapping'].get('task','regression') == 'regression':
        from .engine import run
        return run(payload,directory)
    import numpy as np
    import joblib
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.ensemble import ExtraTreesRegressor, ExtraTreesClassifier, HistGradientBoostingRegressor, HistGradientBoostingClassifier
    from sklearn.linear_model import Ridge, LogisticRegression
    from sklearn.dummy import DummyRegressor, DummyClassifier
    from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold, GroupShuffleSplit
    from sklearn.metrics import mean_absolute_error, balanced_accuracy_score

    train, candidates = payload['training']['rows'], payload['candidates']['rows']
    cfg = payload['mapping']
    target, id_col, group = cfg['target'], cfg['id'], cfg.get('group')
    task = cfg.get('task', 'regression')
    positive = str(cfg.get('positive', '')).strip()
    features = cfg['features']
    if not features or target in features or id_col in features or (group and group in features):
        raise ValueError('请将目标列、候选编号和分组列移出输入特征。')
    if any(c not in payload['training']['columns'] or c not in payload['candidates']['columns'] for c in features):
        raise ValueError('历史表与候选表需要包含相同的输入特征列。')
    if target not in payload['training']['columns'] or id_col not in payload['candidates']['columns']:
        raise ValueError('请选择历史表的目标列和候选表的编号列。')
    train = [r for r in train if str(r.get(target, '')).strip()]
    if len(train) < 6:
        raise ValueError('请补充至少6条有目标结果的记录，再运行模型比较。')
    ids = [str(r.get(id_col, '')).strip() for r in candidates]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError('候选编号不能为空或重复，请在候选表中修正。')
    def number(value):
        if value is None or str(value).strip() == '': return np.nan
        result = float(value)
        if not math.isfinite(result): return np.nan
        return result
    numeric = []
    for j, col in enumerate(features):
        try:
            for row in train: number(row.get(col))
            numeric.append(j)
        except (ValueError, TypeError):
            pass
    categorical = [j for j in range(len(features)) if j not in numeric]
    def matrix(rows):
        result = []
        for row in rows:
            values = []
            for j, col in enumerate(features):
                try: values.append(number(row.get(col)) if j in numeric else str(row.get(col) or '(missing)'))
                except (ValueError, TypeError): raise ValueError(f'列 {col} 应为数值，请修正候选数据。')
            result.append(values)
        return np.array(result, dtype=object)
    x, future = matrix(train), matrix(candidates)
    if task == 'classification':
        labels = sorted(set(str(r[target]).strip() for r in train))
        if len(labels) != 2 or positive not in labels:
            raise ValueError('二分类请选择两个类别中的一个作为希望找到的类别。')
        y = np.array([int(str(r[target]).strip() == positive) for r in train])
        if min(np.bincount(y)) < 2: raise ValueError('每个类别至少需要2条记录。')
        models = [('ET', ExtraTreesClassifier(n_estimators=100, min_samples_leaf=2, random_state=42, n_jobs=2, class_weight='balanced')),
                  ('逻辑回归', LogisticRegression(max_iter=600, class_weight='balanced')),
                  ('梯度提升树', HistGradientBoostingClassifier(max_iter=60, min_samples_leaf=5, random_state=42)),
                  ('简单参照', DummyClassifier(strategy='most_frequent'))]
    else:
        y = np.array([number(r[target]) for r in train])
        if not np.isfinite(y).all(): raise ValueError('目标列包含非有限数值，请修正后重试。')
        models = [('ET', ExtraTreesRegressor(n_estimators=100, min_samples_leaf=2, random_state=42, n_jobs=2)),
                  ('Ridge', Ridge(alpha=1.0)),
                  ('梯度提升树', HistGradientBoostingRegressor(max_iter=60, min_samples_leaf=5, random_state=42)),
                  ('简单参照', DummyRegressor())]
    group_values = None
    if group:
        if group not in payload['training']['columns']: raise ValueError('分组列不存在。')
        group_values = np.array([str(r.get(group) or '') for r in train])
        if any(not g for g in group_values): raise ValueError('请补齐分组列。')
    elif id_col in payload['training']['columns']:
        values = [str(r.get(id_col) or '') for r in train]
        if all(values) and len(set(values)) < len(values): group_values = np.array(values)
    if group_values is not None:
        n = len(set(group_values))
        if n < 2: raise ValueError('需要至少两个独立分组才能比较模型。')
        splits = list(GroupKFold(n_splits=min(3, n)).split(x, y, group_values))
        validation = f'{len(splits)}折按组验证'
    elif task == 'classification':
        splits = list(StratifiedKFold(n_splits=min(3, min(np.bincount(y))), shuffle=True, random_state=42).split(x, y))
        validation = f'{len(splits)}折分层验证'
    else:
        splits = list(KFold(n_splits=3, shuffle=True, random_state=42).split(x))
        validation = '3折验证'
    if task == 'classification' and any(len(set(y[a])) < 2 for a, _ in splits):
        raise ValueError('当前分组使训练部分只剩一个类别，请调整分组或补充数据。')
    def pipeline(model):
        transformers = []
        if numeric:
            transformers.append(('numeric', Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)), ('scale', StandardScaler())]), numeric))
        if categorical:
            transformers.append(('category', OneHotEncoder(handle_unknown='ignore', sparse_output=False, max_categories=32), categorical))
        return Pipeline([('prepare', ColumnTransformer(transformers)), ('model', model)])
    scores = []
    for name, estimator in models:
        values = []
        for a, b in splits:
            p = pipeline(estimator)
            p.fit(x[a], y[a])
            pred = p.predict(x[b])
            values.append(float(balanced_accuracy_score(y[b], pred) if task == 'classification' else mean_absolute_error(y[b], pred)))
        scores.append({'model': name, 'score': float(np.mean(values))})
        (directory / 'progress.json').write_text(json.dumps({'message': f'已完成 {name} 的模型比较'}))
    chosen = min(range(len(scores)), key=lambda i: -scores[i]['score'] if task == 'classification' else scores[i]['score'])
    final = pipeline(models[chosen][1]); final.fit(x, y)
    prediction = final.predict_proba(future)[:, 1] if task == 'classification' else final.predict(future)
    joblib.dump(final, directory / 'model.joblib')
    order = np.argsort(prediction if task == 'regression' and cfg.get('direction') == 'min' else -prediction, kind='stable')
    result = {'kind': 'tabular', 'metric': target, 'unit': cfg.get('unit', ''), 'task': task, 'positive': positive,
              'model': models[chosen][0], 'scores': scores, 'score_label': '平衡准确率' if task == 'classification' else 'MAE',
              'validation': validation, 'training_count': len(train), 'feature_count': len(features),
              'order': [ids[int(i)] for i in order],
              'candidates': [{'id': ident, 'name': ident, 'prediction': float(prediction[i]), 'features': candidates[i]} for i, ident in enumerate(ids)]}
    return result


if __name__ == '__main__':
    folder = Path(sys.argv[1])
    try:
        result = fit(json.loads((folder / 'input.json').read_text()), folder)
        (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        (folder / 'error.json').write_text(json.dumps({'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
