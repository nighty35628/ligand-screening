import json,time
from pathlib import Path
from amadeus import workflow,server
from sklearn.metrics import mean_absolute_error
workflow.init(server,recover=False);p=workflow.create({'title':'材料引擎 · 真实端到端验收','goal':'比较配方与龄期对强度预测的作用'})
workflow.load_material_example(p)
for kind in ('training','candidates'):
 workflow.process_dataset(p,kind,[{'column':'age_day','output':'age_hour','operation':'day_to_hour'},{'column':'age_hour','output':'age_day','operation':'hour_to_day'}])
workflow.save(p);project_id=p['id'];workflow.CANCEL[project_id]=__import__('threading').Event()
workflow.train_table(p)
root=Path('amadeus/examples/concrete');oracle=json.loads((root/'oracle.json').read_text());a=p['analysis'];mae=mean_absolute_error([oracle[c['id']] for c in a['candidates']],[c['prediction'] for c in a['candidates']]);first_selected=p['selected'][:]
workflow.save_plan(p,notes='独立配方候选；回填的是UCI历史实测，非新实验')
workflow.record(p,[{'candidate_id':i,'value':oracle[i],'status':'completed','note':'UCI held-out historical measurement'} for i in p['selected']],source='UCI公开历史实测')
workflow.next_round(p);assert not set(first_selected)&set(p['selected'])
workflow.save(p);assert workflow.load(project_id)['mapping']==p['mapping'];assert len(workflow.load(project_id)['dataset_versions'])==4
report=workflow.export_report(p);out=Path('outputs/engine-e2e');out.mkdir(exist_ok=True);(out/'report.html').write_bytes(report)
first_analysis=a['id'];workflow.train_table(p);assert p['analysis']['training_count']==859+len(first_selected);assert p['analysis_history'][-1]['id']==first_analysis
workflow.save(p)
summary={'project_id':project_id,'first_model':a['model'],'cv_mae':min(s['score'] for s in a['scores']),'independent_candidate_mae':mae,'candidate_count':171,'recommendations':first_selected,'selected_best_measured':max(oracle[i] for i in first_selected),'pool_best':max(oracle.values()),'dataset_versions':len(p['dataset_versions']),'processing_steps':len(p['processing_history']),'retrain_count':p['analysis']['training_count'],'round':p['round'],'second_model':p['analysis']['model']}
(out/'verification.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
