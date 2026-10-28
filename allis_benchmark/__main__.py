"""Run the unified benchmark, verify it independently, or predict with saved RF."""
import argparse
import csv
from datetime import datetime
import itertools
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo

import joblib
import numpy as np

from allis_delivery.core import (ASSETS as COMPONENT_ASSETS, Dataset, check_seal,
    environment, make_seal, quality, read_json, read_json_gzip, require, sha, write_json)
from allis_delivery.evaluation import (compare, expected_best, first_three_mean,
    independent_curve, independent_midrank)
from allis_delivery.workflow import load_candidates
from .core import (ASSETS, METHODS, NAMES, all_ranks, component_predictions,
    fit_rf, predict_rf, protocol, reference_rf)

PACKAGE = Path(__file__).resolve().parent


def code_hashes():
    return {str(p.relative_to(PACKAGE.parent)):sha(p) for folder in (PACKAGE, PACKAGE.parent/'allis_delivery') for p in sorted(folder.glob('*.py'))}


def check_run(run):
    run = Path(run).resolve()
    check_seal(run, run/'input_seal.json')
    meta = read_json(run/'run.json')
    require(meta['code_hashes'] == code_hashes(), 'Code changed after preparation')
    require(meta['environment'] == environment(), 'Environment drift')
    require(meta['protocol_sha256'] == sha(ASSETS/'protocol.json'), 'Protocol drift')
    protocol()
    return run, meta


def rf_worker(run, sid):
    run, meta = check_run(run)
    require(meta['mode']=='baseline-retrain' and sid in meta['split_ids'], 'Invalid worker mode/split')
    require(not (run/'models'/f'{sid}.joblib').exists(), 'Refusing model overwrite')
    write_json(run/'attempts'/f'{sid}.json', {'split':sid,'fits_attempted':1,'started_unix':time.time()})
    start = time.monotonic()
    data = Dataset(); split = data.split(sid)
    model = fit_rf(data, split)
    path = run/'models'/f'{sid}.joblib'
    joblib.dump(model, path, compress=3)
    loaded = joblib.load(path)
    candidate = load_candidates(run/'candidate_inputs'/f'{sid}.npz')
    prediction = predict_rf(loaded, candidate)
    # Prediction from the serialized model is checked against a separately saved historical run.
    ref = reference_rf(data, split)
    errors = {k:float(np.max(abs(np.asarray(prediction[k])-ref[k]))) for k in ref}
    require(max(errors.values()) < 1e-10, f'RF reproduction drift: {errors}')
    require(independent_midrank(prediction['rf_q']) == independent_midrank(ref['rf_q']), 'RF ranks changed')
    require(independent_midrank(prediction['rf_upper_q']) == independent_midrank(ref['rf_upper_q']), 'RF upper ranks changed')
    record = {'split':sid,'train':split['train'],'test':split['test'], **prediction,
              'source':'new_RF_fit_and_saved_model_prediction', 'model_sha256':sha(path),
              'params':loaded.estimator.get_params(), 'reference_errors':errors,
              'seconds':time.monotonic()-start, 'candidate_labels_read':False}
    write_json(run/'rf_predictions'/f'{sid}.json', record)
    return {'split':sid,'fits':1,'seconds':record['seconds'],'max_error':max(errors.values())}


def write_report(run, metrics, execution):
    summary = {r['method']:r for r in metrics['summary']}
    lines = ['# 配体筛选：统一运行结果', '',
        '## Material Passport', '',
        '模式：run / validate；状态：执行完成。来源为公开实测档案，验证类型为固定候选池回顾性比较。', '',
        f"本次新增拟合 {execution['new_fits']} 次，执行耗时 {execution['seconds']:.2f} 秒；两个 ET 组件使用已封存且已真实重训核验的预测（历史30次拟合）。", '',
        '90种配体，每种40个用量点；15池来自3套五折划分，每池36种训练、18种候选。不同池的训练和候选身份重叠，不作为15个独立实验。', '',
        'Q为40点中最高4点相对发光FOM均值。AUR为预算1—5下距本池最好Q的平均差距，越低越好；B1/B3/B5为对应预算选到的最好Q的随机平局期望，越高越好。', '',
        '| 方法 | AUR ↓ | B1 ↑ | B3 ↑ | B5 ↑ |', '|---|---:|---:|---:|---:|']
    for method in METHODS:
        r=summary[method]
        lines.append(f"| {NAMES[method]} | {r['AUR']:.6f} | {r['B1']:.6f} | {r['B3']:.6f} | {r['B5']:.6f} |")
    lines += ['', '## 融合相对各对照', '']
    for c in metrics['comparisons']:
        baseline=summary[c['baseline']]
        percent=100*c['AUR_improvement']/baseline['AUR'] if baseline['AUR'] else 0
        lines.append(f"- 对{NAMES[c['baseline']]}：平均差距缩小 {percent:.2f}%；逐池胜/平/负 {c['wins_ties_losses']}；三套划分的AUR改善 {c['replicate_improvement']}；去掉任一池后最小平均改善 {c['leave_one_pool_out_min_improvement']:.6f}。")
    lines += ['', '## 如何解释', '',
        '成对RF保留42维描述符、实际用量、成对差值回归和全历史参照聚合，使用48树、depth16、leaf2、131072个固定训练对。它是相同筛选任务下的预算适配实现，不是完整逐轮主动学习、原始全对训练或重新寻参复现。', '',
        'RF均值排序是主基线；RF上界排序作为辅助对照完整保留。上界为参照预测均值加Student-t系数乘标准误，参照预测相关，不能当成校准后的物理置信区间。两种规则都在40个已测用量点上取最高4点均值。', '',
        'ET组件使用42维描述符加2048维Morgan；RF使用42维。相对RF的差异包含表示、估计器和决策变化，不能全部归因于融合。融合本身的贡献应与两个同输入ET组件比较。', '',
        '所有15池和预算均报告。该档案经历过前期探索，本次重训用于工程复现，不形成新的独立确认。没有湿实验或真实成本日志，不能换算为已证实的实验次数节省，也不把AUR降幅写成材料发光增幅。', '',
        '## 可复核产物', '',
        '`evaluation/metrics.json`完整指标；`evaluation/per_pool.csv`逐池表；`predictions/`候选预测；`candidate_inputs/`无标签输入；`models/`新RF权重（仅重训模式）；`verification.json`独立复算；`execution.json`实际预算。', '']
    (run/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def evaluate(run):
    run, meta=check_run(run)
    check_seal(run, run/'prediction_seal.json')
    data=Dataset(); rows=[]
    for sid in meta['split_ids']:
        split=data.split(sid); pred=read_json(run/'predictions'/f'{sid}.json')
        gold=quality(data.responses(split['test']))
        for method in METHODS:
            ranking=pred['ranks'][method]; curve=expected_best(ranking,gold)
            rows.append({'split':sid,'replicate':split['replicate'],'scope':'all','method':method,
                'AUR':float(np.mean(max(gold)-curve)), **{f'B{k+1}':float(v) for k,v in enumerate(curve)},
                'curve':curve.tolist(),'top3_mean_Q':first_three_mean(ranking,gold),
                'oracle_Q':float(max(gold)), 'candidate_indices':split['test'], 'gold_Q':gold.tolist(), 'rank':ranking})
    summaries=[]
    for method in METHODS:
        rr=[r for r in rows if r['method']==method]
        summaries.append({'scope':'all','method':method, **{k:float(np.mean([r[k] for r in rr])) for k in ('AUR','B1','B2','B3','B4','B5','top3_mean_Q')},
            'rep_AUR':[float(np.mean([r['AUR'] for r in rr if r['replicate']==i])) for i in sorted({r['replicate'] for r in rr})]})
    metrics={'rows':rows,'summary':summaries,'comparisons':[compare(rows,m,'all') for m in METHODS if m!='equal_rank']}
    write_json(run/'evaluation/metrics.json',metrics)
    with (run/'evaluation/per_pool.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['split','replicate','method','AUR','B1','B2','B3','B4','B5'],extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)
    return metrics


def verify(run, save=True):
    run,meta=check_run(run)
    check_seal(run,run/'prediction_seal.json');check_seal(run,run/'evaluation_seal.json')
    if (run/'model_seal.json').exists():check_seal(run,run/'model_seal.json')
    data=Dataset();metrics=read_json(run/'evaluation/metrics.json')
    # Independent raw-data grouping and top-four computation; no quality()/responses().
    raw=read_json_gzip(COMPONENT_ASSETS/'data/reaction_collection_train_AL0503.json.gz')
    values={ident:[] for ident in data.ids}
    for reaction in raw['reactions']:
        if reaction['properties'].get('WallTag')==1:
            ident=reaction['ligand_solutions'][0]['solute']['identifier']
            if ident in values: values[ident].append(float(reaction['properties']['FigureOfMerit']))
    require(all(len(v)==40 and all(math.isfinite(y) for y in v) for v in values.values()),'Independent label audit failed')
    gold={k:math.fsum(sorted(v,reverse=True)[:4])/4 for k,v in values.items()}
    maxerr=0.; rows_by_key={(r['split'],r['method']):r for r in metrics['rows']}
    require(len(rows_by_key)==len(meta['split_ids'])*len(METHODS),'Incomplete benchmark')
    manual_rows=[]
    for sid in meta['split_ids']:
        s=data.split(sid); p=read_json(run/'predictions'/f'{sid}.json')
        require(p['ids']==[data.ids[i] for i in s['test']] and p['train']==s['train'] and p['test']==s['test'],'Prediction identity drift')
        rr={m:independent_midrank(p[key]) for m,key in [('paired_RF','rf_q'),('paired_RF_CI','rf_upper_q'),('paired_ET','paired_q'),('direct_Q_ET','direct_q')]}
        rr['random']=[1.]*18;rr['equal_rank']=[(a+b)/2 for a,b in zip(rr['paired_ET'],rr['direct_Q_ET'])]
        yy=[gold[ident] for ident in p['ids']]
        for method in METHODS:
            require(rr[method]==p['ranks'][method],'Ranking arithmetic mismatch')
            curve=independent_curve(rr[method],yy)
            r=rows_by_key[sid,method]
            require(r['rank']==rr[method] and r['candidate_indices']==s['test'],'Evaluation identities/ranks mismatch')
            expected={'AUR':math.fsum(max(yy)-float(x) for x in curve)/5, **{f'B{k+1}':float(v) for k,v in enumerate(curve)}}
            err=max(abs(expected[k]-r[k]) for k in expected)
            err=max(err,float(np.max(abs(np.asarray(r['gold_Q'])-yy))))
            maxerr=max(maxerr,err);require(err<1e-10,'Independent metric mismatch')
            manual_rows.append({'method':method,'split':sid,'replicate':s['replicate'],**expected})
    for m in METHODS:
        ss=next(r for r in metrics['summary'] if r['method']==m)
        rows=[r for r in manual_rows if r['method']==m]
        for key in ('AUR','B1','B2','B3','B4','B5'):
            require(abs(ss[key]-math.fsum(r[key] for r in rows)/len(rows))<1e-10,'Summary mismatch')
    # Verify comparisons independently from row-level arithmetic, including leave-one-pool-out.
    for c in metrics['comparisons']:
        dd=[rows_by_key[sid,c['baseline']]['AUR']-rows_by_key[sid,'equal_rank']['AUR'] for sid in meta['split_ids']]
        require(abs(math.fsum(dd)/len(dd)-c['AUR_improvement'])<1e-10,'Comparison mismatch')
        counts=[sum(v>1e-12 for v in dd),sum(abs(v)<=1e-12 for v in dd),sum(v< -1e-12 for v in dd)]
        require(counts==c['wins_ties_losses'],'Win/loss count mismatch')
        if len(dd)>1: require(abs(min((math.fsum(dd)-x)/(len(dd)-1) for x in dd)-c['leave_one_pool_out_min_improvement'])<1e-10,'Leave-one-pool mismatch')
    result={'pass':True,'pools':len(meta['split_ids']),'methods':list(METHODS),'rows':len(manual_rows),
            'independent_max_absolute_error':maxerr,'raw_labels_recomputed':True,'ties_enumerated_exactly':True,
            'all_predictions_sealed_before_evaluation':True,'retrospective':True,'new_blind_confirmation':False}
    if save:write_json(run/'verification.json',result)
    return result


def run_benchmark(output=None, mode='cached', splits='all'):
    start=time.monotonic(); cfg=protocol(); data=Dataset()
    selected=cfg['splits'] if splits=='all' else splits.split(',')
    require(len(selected)==len(set(selected)) and all(s in cfg['splits'] for s in selected),'Invalid splits')
    require(mode in ('cached','baseline-retrain'),'Invalid mode')
    stamp=datetime.now(ZoneInfo('Asia/Hong_Kong')).strftime('%Y%m%d-%H%M%S')
    run=Path(output or f'outputs/project-{stamp}-{uuid.uuid4().hex[:6]}').resolve()
    require(not run.exists() or not any(run.iterdir()),'Output directory must be empty/new')
    for name in ('candidate_inputs','predictions','rf_predictions','models','attempts','logs','evaluation'):(run/name).mkdir(parents=True,exist_ok=True)
    for sid in selected:np.savez_compressed(run/'candidate_inputs'/f'{sid}.npz',**data.candidates(data.split(sid)))
    meta={'mode':mode,'split_ids':selected,'complete_benchmark':selected==cfg['splits'],
          'environment':environment(),'code_hashes':code_hashes(),'protocol_sha256':sha(ASSETS/'protocol.json'),
          'started_unix':time.time(),'historical_ET_component_fits':30,'historical_RF_reference_fits':15,'new_fit_cap':20}
    write_json(run/'run.json',meta)
    make_seal(run,[run/'run.json',*sorted((run/'candidate_inputs').glob('*.npz'))],run/'input_seal.json',stage='prepare')
    deadline=time.monotonic()+cfg['execution_seconds_cap']; completed=[];failure=None
    try:
        for sid in selected:
            s=data.split(sid)
            if mode=='baseline-retrain':
                require(len(list((run/'attempts').glob('*.json')))<cfg['new_fit_cap'],'Fit budget exhausted')
                remaining=deadline-time.monotonic();require(remaining>0,'Time budget exhausted')
                cmd=[sys.executable,'-m','allis_benchmark','_rf','--run-dir',str(run),'--split',sid]
                proc=subprocess.run(cmd,cwd=PACKAGE.parent,capture_output=True,text=True,timeout=min(180,remaining))
                (run/'logs'/f'{sid}.log').write_text(proc.stdout+proc.stderr)
                require(proc.returncode==0,f'RF worker failed; see {run}/logs/{sid}.log')
                print(proc.stdout.strip(),flush=True)
                rf=read_json(run/'rf_predictions'/f'{sid}.json')
                rf={k:rf[k] for k in ('rf_q','rf_upper_q','rf_curves','rf_upper_curves')}
            else:rf=reference_rf(data,s)
            pred={'schema':1,'split':sid,'train':s['train'],'test':s['test'],
                  'ids':[data.ids[k] for k in s['test']],'dose_pmol':data.dose[s['test']].tolist(),
                  **rf,**component_predictions(data,s),'rf_mode':mode,'ET_mode':'verified_historical_predictions'}
            pred['ranks']=all_ranks(pred)
            write_json(run/'predictions'/f'{sid}.json',pred);completed.append(sid)
    except (ValueError,subprocess.TimeoutExpired,OSError) as exc:failure=str(exc)
    execution={'complete':failure is None,'completed_splits':completed,'mode':mode,
               'new_fits':len(list((run/'attempts').glob('*.json'))),'seconds':time.monotonic()-start,
               'failed_attempts':max(0,len(list((run/'attempts').glob('*.json')))-len(list((run/'rf_predictions').glob('*.json')))),
               'failure':failure,'historical_ET_fits':30,'historical_RF_reference_fits':15,'hyperparameter_search':False}
    write_json(run/'execution.json',execution);require(failure is None,failure)
    require(execution['new_fits']<=20 and execution['seconds']<1200,'Execution cap exceeded')
    if mode=='baseline-retrain':make_seal(run,[*sorted((run/'models').glob('*')),*sorted((run/'rf_predictions').glob('*'))],run/'model_seal.json',stage='train')
    make_seal(run,sorted((run/'predictions').glob('*.json')),run/'prediction_seal.json',stage='predict',time=time.time(),candidate_outcomes_read=False)
    metrics=evaluate(run);write_report(run,metrics,execution)
    make_seal(run,[run/'evaluation/metrics.json',run/'evaluation/per_pool.csv',run/'REPORT.md',run/'execution.json'],run/'evaluation_seal.json',stage='evaluate',time=time.time())
    verification=verify(run)
    make_seal(run,[p for p in sorted(run.rglob('*')) if p.is_file()],run/'delivery_seal.json',stage='complete')
    return {'output':str(run),'new_fits':execution['new_fits'],'verification':verification,'summary':metrics['summary']}


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('run');p.add_argument('--mode',choices=['cached','baseline-retrain'],default='cached');p.add_argument('--output',type=Path);p.add_argument('--splits',default='all')
    p=sub.add_parser('_rf');p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--split',required=True)
    p=sub.add_parser('verify');p.add_argument('--run-dir',type=Path,required=True)
    p=sub.add_parser('predict');p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--split',required=True);p.add_argument('--candidates',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();environment()
    if args.cmd=='run':result=run_benchmark(args.output,args.mode,args.splits)
    elif args.cmd=='_rf':result=rf_worker(args.run_dir,args.split)
    elif args.cmd=='verify':result=verify(args.run_dir,save=False)
    else:
        run,meta=check_run(args.run_dir);require(args.split in meta['split_ids'],'Unknown model split')
        check_seal(run,run/'model_seal.json');model=joblib.load(run/'models'/f'{args.split}.joblib')
        require(model.split==args.split,'Model identity mismatch')
        result=predict_rf(model,load_candidates(args.candidates));write_json(args.output,result)
        result={'output':str(args.output),'candidates':len(result['ids']),'candidate_labels_read':False}
    import json
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(2)
