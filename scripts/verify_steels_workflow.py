import json,threading
from pathlib import Path
from amadeus import workflow,server
from sklearn.metrics import mean_absolute_error,r2_score
workflow.init(server,recover=False);p=workflow.create({'title':'钢合金屈服强度 · 真实闭环','goal':'根据化学组成筛选高强度钢合金'});workflow.CANCEL[p['id']]=threading.Event();workflow.load_material_example(p,'steels');workflow.save(p)
workflow.train_table(p);a=p['analysis'];oracle=json.loads(Path('amadeus/examples/steels/oracle.json').read_text());y=[oracle[c['id']] for c in a['candidates']];pred=[c['prediction'] for c in a['candidates']];selected=p['selected'][:];assert len(selected)==3 and len(set(selected))==3
features=p['mapping']['features'];known={c['id']:c for c in a['candidates']};assert len({tuple(known[i]['features'][f] for f in features) for i in selected})==3
workflow.save_plan(p,notes='公开历史数据回顾性验收；组成预测，无处理条件');workflow.historical_results(p);workflow.next_round(p);assert not set(selected)&set(p['selected']);workflow.save(p);q=workflow.load(p['id']);assert q['research_context']['example']=='steels'
out=Path('results/steels-case');out.mkdir(parents=True,exist_ok=True);(out/'report.html').write_bytes(workflow.export_report(q));summary={'project_id':p['id'],'train':a['training_count'],'candidates':len(y),'model':a['model'],'cv_mae':min(s['score'] for s in a['scores']),'holdout_mae':mean_absolute_error(y,pred),'holdout_r2':r2_score(y,pred),'selected':[{'id':i,'formula':known[i]['features']['formula'],'measured':oracle[i]} for i in selected],'pool_best':max(y),'round':p['round'],'recorded':len(p['measurements']),'unique_candidate_inputs':len({tuple(c['features'][f] for f in features) for c in a['candidates']})};(out/'verification.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
