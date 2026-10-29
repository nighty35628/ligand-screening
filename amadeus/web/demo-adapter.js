/* Browser-only demonstration. Predictions are frozen; measurements are public historical data. */
(() => {
'use strict';
const enabled = new URLSearchParams(location.search).has('demo') || !['127.0.0.1','localhost','[::1]'].includes(location.hostname);
if (!enabled) return;
const clone = x => JSON.parse(JSON.stringify(x)), now = () => new Date().toISOString(), uid = () => crypto.randomUUID().slice(0,12);
const key='amadeus-online-projects-v1';
let projects={};try{projects=JSON.parse(localStorage.getItem(key)||'{}');}catch{}
for(const p of Object.values(projects))if(p.operation.status==='running')p.operation={status:'interrupted',message:'演示已暂停，可继续操作。'};
const catalog=fetch('./research-cases.json').then(r=>r.json());
const snapshots={};
async function snapshot(example,cases){const cfg=cases[example];if(!cfg)throw Error('材料案例不存在。');return snapshots[example] ||= fetch('./'+cfg.snapshot).then(r=>{if(!r.ok)throw Error('研究数据暂时未能读取，请重试。');return r.json();}).catch(e=>{delete snapshots[example];throw e;});}
const fixture=fetch('./demo-case.json').then(r=>{if(!r.ok)throw Error('案例数据暂时未能加载，请刷新重试。');return r.json();});
function save(p){p.updated=now();p.revision++;projects[p.id]=p;try{localStorage.setItem(key,JSON.stringify(projects));}catch{ /* Keep the active session usable if browser storage is full. */ }}
function select(p){const done=new Set(p.measurements.filter(m=>m.status==='completed'&&m.analysis_id===p.analysis?.id).map(m=>m.candidate_id));p.selected=(p.analysis?.order||[]).filter(id=>!p.excluded.includes(id)&&!done.has(id)).slice(0,p.task.budget);}
const current=p=>p.plans.filter(x=>x.round===p.round).at(-1);
const names=p=>p.selected.map(id=>p.analysis.candidates.find(c=>c.id===id)?.name||id).join('、');
function plan(p,args={}){if(!p.selected.length)throw Error('先选择本轮候选。');const previous=current(p);p.plans.push({id:uid(),round:p.round,version:(previous?.version||0)+1,analysis_id:p.analysis.id,created:now(),goal:p.task.goal,items:args.items||p.selected.map(id=>({candidate_id:id,name:p.analysis.candidates.find(c=>c.id===id).name,condition:'',metric:p.task.metric,unit:p.task.unit||'',note:''})),notes:args.notes||'',recommended:[...p.selected],sources:[]});}
function record(p,rows,source){const pl=current(p);if(!pl)throw Error('先保存本轮实验计划。');for(const row of rows){if(!pl.items.some(i=>i.candidate_id===row.candidate_id))throw Error('结果需要对应当前计划中的候选。');const value=row.value===''||row.value==null?null:Number(row.value);if(value!==null&&!Number.isFinite(value))throw Error('请填写有效数值。');p.measurements.push({...row,value,id:uid(),plan_id:pl.id,round:p.round,analysis_id:p.analysis.id,created:now(),unit:row.unit||'',condition:row.condition||'',note:row.note||'',status:row.status||'completed',source});}}
function historical(p,f){const pl=current(p);if(!pl)throw Error('先保存本轮计划，再查看对应的历史实测。');const rows=pl.items.filter(i=>!p.measurements.some(m=>m.plan_id===pl.id&&m.candidate_id===i.candidate_id&&m.source==='公开历史实测')).map(i=>({...i,value:f.truth[i.candidate_id].value,status:'completed',note:'40点曲线最高4点的平均相对发光表现'}));record(p,rows,'公开历史实测');for(const i of pl.items)p.analysis.candidates.find(c=>c.id===i.candidate_id).measured_curve=clone(f.truth[i.candidate_id].curve);p.analysis.evidence=clone(f.evidence);}
function next(p){if(!p.measurements.some(m=>m.round===p.round))throw Error('先记录本轮结果。');p.round++;select(p);}
function load(p,f){p.research_context={};p.analysis=clone(f.analysis);p.task.metric=p.analysis.metric;p.task.direction='max';p.task.unit='';select(p);}
function summary(p){const results=p.measurements.filter(m=>m.value!=null&&m.analysis_id===p.analysis?.id).sort((a,b)=>b.value-a.value);const label=p.research_context?.label||'历史实测';return `研究报告已整理完成。\n\n目标：${p.task.goal}\n方法：${p.analysis?.model||'候选排序'}。\n已保存 ${p.plans.length} 份计划，记录 ${p.measurements.length} 条结果，当前第 ${p.round} 轮。${results.length?'\n\n本轮最好'+label+'：'+results[0].candidate_id+'，'+p.task.metric+' = '+results[0].value.toFixed(3)+' '+(p.task.unit||'')+'。':''}\n\n报告包含模型比较、候选预测、计划与已记录结果。下一轮沿用已有排序，跳过已记录和已排除的候选。`;}
function materialHistory(p,m){const pl=current(p);if(!pl)throw Error('先保存计划。');const source='公开'+p.research_context.label;record(p,pl.items.filter(i=>!p.measurements.some(x=>x.plan_id===pl.id&&x.candidate_id===i.candidate_id)).map(i=>({...i,value:m.oracle[i.candidate_id],status:'completed',note:source})),source);}
function chat(p,text,f,m){let reply='';p.messages.push({role:'user',content:text,at:now()});
 if(/总结|报告/.test(text)){reply=summary(p);}
 else if(/下一轮/.test(text)&&p.analysis){next(p);reply=`已安排第 ${p.round} 轮，优先候选：${names(p)}。\n\n已记录结果和已排除的候选不再重复推荐。`;}
 else if(/实测|历史结果|计算参考|参考值/.test(text)&&p.analysis?.kind==='tabular'){materialHistory(p,m);reply='已记录本轮候选的公开'+p.research_context.label+'，可在右侧对比预测与参考结果。';}
 else if(/实测|历史结果/.test(text)&&p.analysis){historical(p,f);reply='已载入本轮候选的公开历史实测结果。\n\n'+current(p).items.map(i=>`${i.name}：Q = ${f.truth[i.candidate_id].value.toFixed(3)}`).join('\n')+'\n\n右侧可以查看测量记录及同预算方法对照。';}
 else if(/保存|计划/.test(text)&&p.analysis){plan(p);reply=`已保存第 ${p.round} 轮计划，包含 ${names(p)}。\n\n可以在右侧补充测试条件和备注，再记录实验结果。`;}
 else if(/买不到|换一个|名额|改为/.test(text)&&p.analysis){if(/买不到|换一个/.test(text)&&p.selected.length)p.excluded.push(p.selected[/第二|第2/.test(text)?1:0]);const n=text.match(/(?:改为|测试|名额)\s*(\d+)/);if(n)p.task.budget=Math.max(1,Math.min(18,+n[1]));select(p);reply=`已调整本轮名单，测试名额为 ${p.task.budget}：${names(p)}。\n\n按当前模型的候选排名补位，已排除的候选不会再次入选。`;}
 else if(p.analysis?.kind==='tabular'){reply='当前研究使用 '+p.analysis.model+' 分析 '+p.analysis.candidates.length+' 条候选。可以在右侧查看模型对照、修改测试名额、保存计划和记录结果，也可以让我总结报告。';}
 else if(/CsPb|钙钛矿|纳米晶|配体|发光/i.test(text)){const n=text.match(/测试\s*(\d+)/);if(n)p.task.budget=Math.max(1,Math.min(18,+n[1]));load(p,f);reply=`当前案例包含 18 种候选配体，使用 36 种历史配体的已保存模型结果。\n\n本轮优先候选：${names(p)}。\n\n成对 ET 预测用量响应，直接评分 ET 预测整体表现，两路名次等权融合。评价指标 Q 为40个用量点中最高4点的平均相对发光表现。你可以调整名单、保存计划，再查看对应的历史实测结果。`;}
 else reply='这个在线版本可以完整体验纳米晶发光优化流程。在首页点击“选择这个研究”，即可查看候选推荐、调整计划、录入结果和生成图文报告。自定义研究分析在本机工作台运行。';
 p.messages.push({role:'assistant',content:reply,at:now()});
}
function action(p,action,args,f,m,cases){const example=args.example||(action==='material_example'?'concrete':p.research_context?.example);const cfg=cases[example];switch(action){
case 'material_example':
 if(p.analysis)p.analysis_history.push(clone(p.analysis));
 if(p.plans.length||p.measurements.length)p.round=Math.max(p.round,...p.plans.map(x=>x.round))+1;
 p.datasets=clone(m.datasets);p.mapping=clone(m.mapping);p.dataset_versions=clone(m.versions);p.processing_history=[];p.extraction_drafts=[];p.analysis=null;p.selected=[];p.excluded=[];
 p.research_context={material:cfg.material,example,label:cfg.label};
 p.task={goal:cfg.goal,budget:3,metric:m.mapping.target,direction:'max',unit:cfg.unit};
 p.sources=[{title:cfg.source_title,url:m.provenance.source,summary:cfg.description+' · 公开'+cfg.label}];
 if(args.replay){p.analysis={...clone(m.analysis),id:uid()};select(p);p.messages.push({role:'assistant',content:`已整理 ${m.analysis.training_count} 条历史记录和 ${m.analysis.candidates.length} 条候选。沿用已完成的特征与模型比较，采用 ${m.analysis.model}。本轮优先建议已列在右侧，可调整名单、保存计划，再查看对应的${cfg.label}。`,at:now()});}
 break;
case 'train':
 if(!cfg)throw Error('自定义训练请使用本机引擎。');
 if(JSON.stringify(args.mapping||p.mapping)!==JSON.stringify(m.mapping))throw Error('在线版提供固定配置真实运行回放；修改配置请在本机运行。');
 if(p.analysis){select(p);p.messages.push({role:'assistant',content:'当前显示已保存的模型结果。新的记录已保留，下一轮沿用已有排序；重新训练可在本机工作台执行。',at:now()});break;}
 p.analysis={...clone(m.analysis),id:uid()};select(p);p.messages.push({role:'assistant',content:'已读取真实训练快照：五折分组验证、特征组与模型对照、Top-K贝叶斯搜索。',at:now()});break;
case 'chat':chat(p,args.message,f,m);break;
case 'specialist':load(p,f);break;
case 'task':p.task={...p.task,...args,budget:Math.max(1,Math.min(p.analysis?.candidates.length||18,Number(args.budget)||3))};select(p);break;
case 'adjust':p.excluded=[...new Set([...p.excluded,...(args.exclude||[])])].filter(x=>!(args.restore||[]).includes(x));select(p);break;
case 'save_plan':plan(p,args);break;
case 'history_results':if(cfg)materialHistory(p,m);else historical(p,f);break;
case 'record':record(p,args.records,'用户录入');break;
case 'next_round':next(p);break;
default:throw Error('自有数据训练和资料检索请在本机工作台运行。');}}
window.AmadeusDemo={
 async api(path,body){const [f,cases]=await Promise.all([fixture,catalog]);if(path==='/api/config')return {local:true,configured:false,demo:true};if(path==='/api/projects'){if(!body)return clone(Object.values(projects).sort((a,b)=>b.updated.localeCompare(a.updated)));const p={id:uid(),title:body.title,created:now(),updated:now(),round:1,revision:0,task:{goal:body.goal||'',budget:3,metric:'相对发光 Q',direction:'max'},analysis:null,analysis_history:[],excluded:[],selected:[],plans:[],measurements:[],messages:[],sources:[],actions:[],datasets:{},mapping:{},receipts:[],operation:{status:'idle',message:''}};save(p);return clone(p);}
 const match=path.match(/^\/api\/projects\/([^/]+)(?:\/(\w+))?$/);const p=projects[match?.[1]];if(!p)throw Error('未找到此浏览器中的项目，请创建新的演示。');if(!match[2])return clone(p);
 if(match[2]==='cancel'){p.operation={id:uid(),status:'interrupted',message:'演示已停止。'};save(p);return clone(p);}
 if(match[2]==='action'){const example=body.args?.example||(body.action==='material_example'?'concrete':p.research_context?.example);const m=cases[example]?await snapshot(example,cases):null;const id=body.operation_id||uid();p.operation={id,status:'running',message:body.action==='chat'?'正在整理候选与研究记录…':'正在更新研究工作区…'};save(p);setTimeout(()=>{if(p.operation.id!==id||p.operation.status!=='running')return;try{action(p,body.action,body.args||{},f,m,cases);p.operation={id,status:'complete',message:'已完成'};}catch(e){p.operation={id,status:'failed',message:e.message};}save(p);},900+Math.random()*650);return clone(p);}
 throw Error('此操作暂不支持。');
 }
};
})();
