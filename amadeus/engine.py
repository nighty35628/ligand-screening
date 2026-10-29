"""Versioned regression experiments: grouped CV, feature recipes and nested optimization."""
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from .tabular import parse_csv


def seeded_mi(x, y):
    from sklearn.feature_selection import mutual_info_regression
    return mutual_info_regression(x,y,random_state=42)


def run(payload, directory):
    import joblib
    import optuna
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.feature_selection import SelectKBest, mutual_info_regression
    from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.dummy import DummyRegressor
    from sklearn.model_selection import GroupKFold, KFold
    from sklearn.metrics import mean_absolute_error
    from xgboost import XGBRegressor
    from lightgbm import LGBMRegressor
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    start=time.monotonic(); directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    cfg=payload['mapping'];target=cfg['target'];idcol=cfg['id'];seed=int(cfg.get('seed',42))
    train=[r for r in payload['training']['rows'] if str(r.get(target,'')).strip()]
    future=payload['candidates']['rows'];features=cfg['features']
    forbidden={target,idcol,cfg.get('group','')}
    if not features or forbidden.intersection(features):raise ValueError('输入特征不能包含标签、编号或分组列。')
    if len(train)<10 or not future:raise ValueError('需要至少10条历史记录和非空候选表。')
    ids=[str(r.get(idcol,'')) for r in future]
    if not all(ids) or len(set(ids))!=len(ids):raise ValueError('候选编号必须非空且唯一。')
    if any(f not in r for r in train+future for f in features):raise ValueError('历史表和候选表缺少输入列。')
    y=np.array([float(r[target]) for r in train]);assert np.isfinite(y).all(),'目标包含非有限值'
    def numeric(col):
        try:
            vals=[float(r[col]) for r in train if r.get(col) not in ('',None)]
            return bool(vals) and all(np.isfinite(vals))
        except (ValueError,TypeError):return False
    numeric_cols={f for f in features if numeric(f)}
    def matrix(rows,cols):
        return np.array([[float(r[f]) if r.get(f) not in ('',None) else np.nan if f in numeric_cols else '(missing)' for f in cols] for r in rows],dtype=object) if all(f in numeric_cols for f in cols) else np.array([[((float(r[f]) if r.get(f) not in ('',None) else np.nan) if f in numeric_cols else str(r.get(f) or '(missing)')) for f in cols] for r in rows],dtype=object)
    group=cfg.get('group');groups=np.array([str(r.get(group,'')) for r in train]) if group else None
    if groups is not None and any(not x for x in groups):raise ValueError('分组列存在缺失。')
    if groups is None and len({str(r.get(idcol,'')) for r in train})<len(train):groups=np.array([str(r[idcol]) for r in train])
    # Identical inputs must remain together even if a user omitted the group column.
    identities=[tuple(str(r[f]) for f in features) for r in train]
    if groups is None and len(set(identities))<len(identities):groups=np.array([hashlib.sha256(repr(x).encode()).hexdigest() for x in identities])
    def split(indices,n):
        if groups is not None:
            count=min(n,len(set(groups[indices])))
            if count<2:raise ValueError('至少需要两个独立分组。')
            return list(GroupKFold(count).split(indices,groups=groups[indices]))
        return list(KFold(min(n,len(indices)),shuffle=True,random_state=seed).split(indices))
    idx=np.arange(len(train));outer=split(idx,5)
    recipes={k:[f for f in cols if f in features] for k,cols in cfg.get('feature_groups',{}).items()}
    recipes={k:v for k,v in recipes.items() if v};recipes['combined']=features
    def estimator(name,params):
        common={'n_estimators':80,'random_state':seed,'n_jobs':1}
        if name=='RF':return RandomForestRegressor(**(common|params))
        if name=='ET':return ExtraTreesRegressor(**(common|params))
        if name=='XGBoost':return XGBRegressor(**(common|{'max_depth':4,'learning_rate':.08}|params))
        if name=='LightGBM':return LGBMRegressor(**(common|{'verbosity':-1,'min_child_samples':10}|params))
        if name=='Ridge':return Ridge(alpha=1)
        return DummyRegressor()
    def pipeline(cols,name,params=None,k='all'):
        nums=[i for i,f in enumerate(cols) if f in numeric_cols];cats=[i for i,f in enumerate(cols) if f not in numeric_cols];parts=[]
        if nums:parts.append(('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),nums))
        if cats:parts.append(('category',OneHotEncoder(handle_unknown='ignore',sparse_output=False),cats))
        return Pipeline([('prepare',ColumnTransformer(parts)),('select','passthrough' if k=='all' else SelectKBest(seeded_mi,k=k)),('model',estimator(name,params or {}))])
    results=[];predictions={};models=['Dummy','Ridge','RF','ET','XGBoost','LightGBM'];progress=lambda msg:(directory/'progress.json').write_text(json.dumps({'message':msg}))
    (directory/'split_manifest.json').write_text(json.dumps({'seed':seed,'group_column':group,'folds':[{'train':[int(i) for i in a],'test':[int(i) for i in b]} for a,b in outer],'row_ids':[str(r.get(idcol,i)) for i,r in enumerate(train)]},indent=2))
    def assess(name,cols,recipe,tuned=False):
        oof=np.zeros(len(y));folds=[];choices=[]
        for fold,(a,b) in enumerate(outer):
            if groups is not None:assert not set(groups[a])&set(groups[b])
            params,k,study=optimize(name,cols,a,f'{recipe}-{name}-{fold}') if tuned else ({},'all',None)
            model=pipeline(cols,name,params,k);x=matrix(train,cols);model.fit(x[a],y[a]);oof[b]=model.predict(x[b]);folds.append(float(mean_absolute_error(y[b],oof[b])));choices.append({'params':params,'k':k})
        label=f'{recipe} / {name}'+(' / optimized' if tuned else '')
        predictions[label]=oof.tolist();entry={'model':label,'estimator':name,'recipe':recipe,'optimized':tuned,'score':float(mean_absolute_error(y,oof)),'fold_mae':folds,'fold_choices':choices,'features':cols}
        # Candidate screening within each held-out fold, using identical fold pools.
        entry['screening']={}
        for budget in (1,3,5):
            regrets=[];hits=[];best=[]
            for _,b in outer:
                order=np.argsort(oof[b] if cfg.get('direction')=='min' else -oof[b],kind='stable');chosen=b[order[:min(budget,len(b))]]
                lo=cfg.get('direction')=='min';value=float(np.min(y[chosen]) if lo else np.max(y[chosen]));oracle=float(np.min(y[b]) if lo else np.max(y[b]));regrets.append(abs(oracle-value));best.append(value);hits.append(float(np.any(np.isclose(y[chosen],oracle))))
            entry['screening'][str(budget)]={'mean_regret':float(np.mean(regrets)),'mean_selected_best':float(np.mean(best)),'best_hit_rate':float(np.mean(hits))}
        results.append(entry);progress('已完成 '+label);(directory/'leaderboard.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    trials=int(cfg.get('search_trials',4));studies=[]
    if cfg.get('optimize') and trials<1:raise ValueError('搜索次数至少为1。')
    def optimize(name,cols,indices,label):
        x=matrix(train,cols);inner=split(indices,3)
        study=optuna.create_study(direction='minimize',sampler=optuna.samplers.TPESampler(seed=seed,n_startup_trials=2),storage=f'sqlite:///{directory.resolve()}/search.sqlite3',study_name=label,load_if_exists=True)
        def objective(trial):
            k=trial.suggest_categorical('k',['all']+list(sorted({1,max(1,len(cols)//2)})))
            if name in ('ET','RF'):params={'min_samples_leaf':trial.suggest_int('min_samples_leaf',1,8),'max_features':trial.suggest_float('max_features',.5,1)}
            else:params={'learning_rate':trial.suggest_float('learning_rate',.02,.2,log=True),'max_depth':trial.suggest_int('max_depth',2,6)}
            scores=[]
            for ia,ib in inner:
                m=pipeline(cols,name,params,k);a,b=indices[ia],indices[ib];m.fit(x[a],y[a]);pred=m.predict(x[b])
                if cfg.get('selection_metric')=='regret':
                    lo=cfg.get('direction')=='min';order=np.argsort(pred if lo else -pred,kind='stable');oracle=np.min(y[b]) if lo else np.max(y[b]);scores.append(float(np.mean([abs(oracle-(np.min(y[b][order[:min(k,len(b))]]) if lo else np.max(y[b][order[:min(k,len(b))]]))) for k in (1,3,5)])))
                else:scores.append(mean_absolute_error(y[b],pred))
            trial.set_user_attr('estimator_params',params);return float(np.mean(scores))
        remaining=max(0,trials-sum(t.state==optuna.trial.TrialState.COMPLETE for t in study.trials));study.optimize(objective,n_trials=remaining)
        best=study.best_trial;studies.append({'name':label,'best_inner_score':best.value,'metric':cfg.get('selection_metric','mae'),'params':best.params,'trials':len(study.trials)})
        return best.user_attrs['estimator_params'],best.params['k'],study
    for recipe,cols in recipes.items():
        for name in models:assess(name,cols,recipe)
    if cfg.get('optimize',False):
        for name in ('RF','ET','XGBoost','LightGBM'):assess(name,features,'combined',True)
    def selection_score(r):
        if cfg.get('selection_metric','mae')=='regret':return np.mean([v['mean_regret'] for v in r['screening'].values()])
        return r['score']
    winner=min(results,key=selection_score);cols=winner['features'];name=winner['estimator']
    params,k,_=optimize(name,cols,idx,'final-'+name) if winner['optimized'] else ({},'all',None)
    final=pipeline(cols,name,params,k);final.fit(matrix(train,cols),y);future_prediction=final.predict(matrix(future,cols));joblib.dump(final,directory/'model.joblib')
    assert np.allclose(future_prediction,joblib.load(directory/'model.joblib').predict(matrix(future,cols)))
    feature_names=final['prepare'].get_feature_names_out();selected=feature_names.tolist() if final['select']=='passthrough' else feature_names[final['select'].get_support()].tolist()
    order=np.argsort(future_prediction if cfg.get('direction')=='min' else -future_prediction,kind='stable')
    result={'kind':'tabular','metric':target,'unit':cfg.get('unit',''),'task':'regression','model':winner['model'],'scores':results,'score_label':'MAE','validation':f'{len(outer)}折'+('按组验证' if groups is not None else '验证'),'training_count':len(train),'feature_count':len(cols),'selected_features':selected,'search':studies,'seconds':round(time.monotonic()-start,2),'selection_metric':cfg.get('selection_metric','mae'),'evaluation_note':'同一CV用于开发比较和最终配置选择；独立候选标签不参与训练或调参。','order':[ids[int(i)] for i in order],'candidates':[{'id':ident,'name':ident,'prediction':float(future_prediction[i]),'features':future[i]} for i,ident in enumerate(ids)]}
    (directory/'oof_predictions.json').write_text(json.dumps(predictions));(directory/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));(directory/'run_config.json').write_text(json.dumps({'mapping':cfg,'data_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()},ensure_ascii=False,indent=2))
    return result
