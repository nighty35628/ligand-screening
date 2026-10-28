'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (x, n=3) => Number(x).toFixed(n);
  const rankText = n => Number.isInteger(n) ? String(n) : String(Number(n.toFixed(2)));
  const paths = {
    arrow:'M4 12h16m-6-6 6 6-6 6', folder:'M3 7h7l2 2h9v11H3zM3 7V4h7l2 3',
    task:'M8 5h12M8 12h12M8 19h12M3 4v2M3 11v2M3 18v2',
    molecule:'M6 6h12v12H6zM3 3l3 3m12 0 3-3M3 21l3-3m12 0 3 3',
    chart:'M4 3v17h17M7 15l4-5 4 2 5-7', report:'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h8',
    check:'m5 12 4 4L19 6', clock:'M12 7v5l3 2M3 11a9 9 0 1 1 3 8M3 4v7h7',
    lock:'M6 10h12v11H6zM8 10V6a4 4 0 0 1 8 0v4', download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5'
  };
  const icon = (name, cls='') => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.task}"/></svg>`;
  const META = {
    random:{name:'随机选择',color:'#79847b'}, paired_RF:{name:'成对 RF 基线',color:'#816087'},
    paired_RF_CI:{name:'RF 上界排序',color:'#967b36'}, paired_ET:{name:'曲线预测 · 成对 ET',color:'#32679d'},
    direct_Q_ET:{name:'直接评分 · ET',color:'#9a5737'}, equal_rank:{name:'Amadeus · 融合推荐',color:'#275e47'}
  };
  const MAIN_METHODS = ['random','paired_RF','paired_ET','direct_Q_ET','equal_rank'];
  const VIEWS = {setup:'任务设置',results:'实验建议',evidence:'实测对照',report:'决策报告',history:'运行记录',running:'正在分析'};
  let C, archive, local=false, view='setup', poolId='r0_f0', budget=3, mode='live', job=null, truth=null, selected=0, evidenceScope='pool', error='', history=[];
  let busy=false;
  const basePool = () => C.pools.find(p=>p.id===poolId);
  const current = () => job.result;
  const mol = i => C.molecules[current().test[i]];
  const name = m => m.name===m.smiles ? `配体 ${m.label}` : m.name;
  const modeName = m => m==='live' ? '本机模型推断' : '历史预测回放';
  const day = t => new Date(t).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});

  async function api(path, options){
    const response=await fetch(path, options);
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || '请求未完成，请重试。');
    return data;
  }
  function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4000);}
  function navigate(next){view=next;error='';render();window.scrollTo({top:0,behavior:'instant'});$('main').focus({preventScroll:true});}
  function header(title, description, action=''){
    return `<div class="page-head"><div><h1>${title}</h1><p>${description}</p></div>${action?`<div class="actions">${action}</div>`:''}</div>`;
  }
  function navigation(){
    $('navigation').innerHTML=[['setup','task','任务设置'],['results','molecule','实验建议'],['evidence','chart','实测对照'],['report','report','决策报告'],['history','clock','运行记录']].map(([key,glyph,label])=>`<button class="nav-item ${view===key||(view==='running'&&key==='setup')?'active':''}" data-view="${key}" ${busy || (!['setup','history'].includes(key)&&job?.status!=='complete')?'disabled':''} ${view===key?'aria-current="page"':''} aria-label="${label}">${icon(glyph)}<span class="nav-text">${label}</span>${view===key?'<span class="nav-dot"></span>':''}</button>`).join('');
    $('page-name').textContent=VIEWS[view];
    $('mode-badge').textContent=local ? '本机工作台' : '在线演示 · 历史回放';
    $('connection').textContent=local ? '本地服务已连接' : '演示资源已载入';
    document.querySelector('[data-action="history"]').disabled=busy;
  }
  function setup(){
    const p=basePool(), preview=p.test.slice(0,6).map(i=>C.molecules[i]);
    return header('安排下一轮实验','从已有数据出发，比较候选，生成一份可追溯的测试建议。')+
    `<div class="setup-grid"><section class="surface setup-form" aria-label="研究任务设置"><div class="case-heading"><div class="case-icon">${icon('molecule')}</div><div><h2>纳米晶发光优化</h2><p>材料研发 · CsPbBr₃表面配体筛选</p></div></div>
    <label class="field"><span class="field-label">研究目标</span><select id="objective"><option>优先找到发光表现更好的配体</option></select></label>
    <label class="field"><span class="field-label">候选数据</span><select id="pool">${C.pools.map((x,i)=>`<option value="${x.id}" ${x.id===poolId?'selected':''}>候选组 ${String(i+1).padStart(2,'0')} · ${x.test_count}种配体${x.live?' · 已安装模型':''}</option>`).join('')}</select></label>
    <div class="field"><span class="field-label" id="budget-label">本轮测试名额</span><div class="budget-group" role="group" aria-labelledby="budget-label">${[1,2,3,4,5].map(n=>`<button class="budget-button ${budget===n?'active':''}" data-budget="${n}" aria-pressed="${budget===n}">${n} 个</button>`).join('')}</div><p class="field-note">按配体计数，每种配体对应一条40点用量曲线。</p></div>
    <div class="field"><span class="field-label">运行方式</span><div class="mode-options"><button class="mode-option ${mode==='live'?'active':''}" data-mode="live" aria-pressed="${mode==='live'}" ${!local||!p.live?'disabled':''}>本机模型推断<small>加载已有模型，实际计算</small></button><button class="mode-option ${mode==='replay'?'active':''}" data-mode="replay" aria-pressed="${mode==='replay'}">快速回放<small>复用预测，重新融合排名</small></button></div>${!p.live?'<p class="field-note">本组提供历史回放。候选组01可在本机加载模型。</p>':''}</div>
    ${error?`<div class="error" role="alert">${esc(error)}</div>`:''}<button class="button primary full" data-action="run">开始分析 ${icon('arrow')}</button><div class="dataset-summary"><span>${p.train_count}个已测配体作参考</span><span>${p.test_count}个候选</span></div></section>
    <section class="setup-preview"><div class="preview-intro"><h2>待比较的候选</h2><p>分子结构不同，用量与发光响应也可能不同。</p></div><div class="molecule-sheet"><div class="sheet-toolbar"><span>候选结构预览</span><span>6 / ${p.test_count}</span></div><div class="sheet-grid">${preview.map(m=>`<div class="specimen"><div class="structure" role="img" aria-label="${esc(name(m))}结构">${m.svg}</div><span class="label">${esc(m.label)}</span><span class="formula">${esc(m.formula)}</span></div>`).join('')}</div></div>
    <div class="workflow-strip"><span>历史数据</span>${icon('arrow')}<span>双模型预测</span>${icon('arrow')}<span>融合推荐</span>${icon('arrow')}<span>实测对照</span></div>
    <p class="context-note"><strong>为什么从配体开始？</strong><br>配体附着在纳米晶表面，分子结构与加入量都会影响发光。Amadeus结合用量曲线与整体表现两路判断，帮助安排下一轮优先测试的候选。<br><br>本例使用90种配体的公开实测档案。候选答案在推荐之后揭晓。</p></section></div>`;
  }
  function running(){
    const stages=[['检查任务与数据','读取36种历史配体、18个候选及实际用量。'],['执行两路预测',mode==='live'?'加载已保存权重，计算响应曲线与整体表现。':'读取已核验的曲线预测与直接评分。'],['合并候选排名','两路名次各占50%，固定规则生成优先级。'],['保存实验建议','保留运行记录，准备名单和决策报告。']];
    return header('正在形成实验建议','配置已固定。此次运行复用已有模型，不进行训练或调参。')+
      `<div class="run-layout"><ol class="run-stages">${stages.map(([title,desc],i)=>`<li class="${i<job.stage?'done':i===job.stage?'current':''}"><span class="stage-number">${i<job.stage?'✓':i+1}</span><div><h3>${title}</h3><p>${desc}</p></div></li>`).join('')}</ol><section class="surface run-summary"><h2>本次任务</h2><dl><dt>研究案例</dt><dd>CsPbBr₃发光优化</dd><dt>候选组</dt><dd>${esc(poolId)}</dd><dt>测试名额</dt><dd>${budget} / 18</dd><dt>运行方式</dt><dd>${modeName(mode)}</dd></dl><p role="status" aria-live="polite">${esc(job.message)}</p><p class="run-time">${mode==='live'?'模型推断通常需要数秒至几十秒。':'读取历史预测并复算排名。'}</p></section></div>`;
  }
  function chart(series,{xLabel='配体用量 / nmol',yLabel='相对发光 FOM',domainX=null,domainY=null}={}){
    const w=560,h=244,l=43,r=16,t=29,b=42;
    const pts=series.flatMap(s=>s.points).filter(p=>p.every(Number.isFinite));
    let [xmin,xmax]=domainX||[Math.min(...pts.map(p=>p[0])),Math.max(...pts.map(p=>p[0]))];
    let [ymin,ymax]=domainY||[Math.min(0,...pts.map(p=>p[1])),Math.max(...pts.map(p=>p[1]))*1.1];
    if(xmin===xmax)xmax=xmin+1;if(ymin===ymax)ymax=ymin+1;
    const x=v=>l+(v-xmin)/(xmax-xmin)*(w-l-r),y=v=>h-b-(v-ymin)/(ymax-ymin)*(h-t-b);
    let svg=`<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(yLabel)}与${esc(xLabel)}"><title>${esc(yLabel)}与${esc(xLabel)}</title><text x="${l}" y="13">${esc(yLabel)}</text>`;
    for(let i=0;i<=4;i++){let v=ymin+(ymax-ymin)*i/4;svg+=`<line class="grid" x1="${l}" y1="${y(v)}" x2="${w-r}" y2="${y(v)}"/><text x="${l-9}" y="${y(v)+3}" text-anchor="end">${fmt(v,1)}</text>`;}
    for(let i=0;i<5;i++){let v=xmin+(xmax-xmin)*i/4;svg+=`<text x="${x(v)}" y="${h-b+19}" text-anchor="middle">${Number(v.toFixed(1))}</text>`;}
    for(const s of series){svg+=`<polyline points="${s.points.map(p=>`${x(p[0])},${y(p[1])}`).join(' ')}" fill="none" stroke="${s.color}" stroke-width="${s.main?3:2}" ${s.dash?'stroke-dasharray="5 4"':''} stroke-linecap="round" stroke-linejoin="round"/>`;if(s.dots)svg+=s.points.map(p=>`<circle cx="${x(p[0])}" cy="${y(p[1])}" r="3" fill="${s.color}"/>`).join('');}
    return svg+`<text x="${(w+l-r)/2}" y="${h-3}" text-anchor="middle">${esc(xLabel)}</text></svg>`;
  }
  function legend(methods){return `<div class="legend">${methods.map(k=>`<span style="color:${META[k].color}"><i></i>${META[k].name}</span>`).join('')}</div>`;}
  function reason(i){
    const r=current().ranks,a=r.paired_ET[i],b=r.direct_Q_ET[i],diff=Math.abs(a-b);
    if(!current().selected.includes(i))return diff<=3
      ? '两路模型的排序较接近，但在当前测试名额下列为备选。'
      : `两路名次相差${rankText(diff)}，当前融合排名未进入本轮名单，可作为后续备选查看。`;
    if(Math.max(a,b)<=job.budget)return `两路模型都将它排在前${job.budget}名，推荐依据较一致。`;
    if(diff<=3)return '两路模型的排序较接近，合并后进入本轮优先名单。';
    return `${a<b?'曲线预测':'直接评分'}更看好这个候选，两路名次相差${rankText(diff)}。建议结合曲线进一步检查。`;
  }
  function detail(){
    const p=current(),m=mol(selected),i=selected,r=p.ranks;
    const series=[{color:META.paired_ET.color,main:true,points:p.paired_curves[i].map((v,j)=>[p.dose_pmol[i][j]/1000,v])},{color:META.paired_RF.color,dash:true,points:p.rf_curves[i].map((v,j)=>[p.dose_pmol[i][j]/1000,v])}];
    const gold=truth?.molecules.find(x=>x.index===p.test[i]);
    if(gold)series.push({color:'#203c34',points:gold.gold_curve.map((v,j)=>[p.dose_pmol[i][j]/1000,v])});
    return `<div class="detail-layout"><section class="surface curve-panel"><div class="section-head"><div><h2>${esc(name(m))}</h2><p>${esc(m.label)} · ${esc(m.formula)}</p></div><span class="pill">${gold?'已揭晓实测':'预测用量响应'}</span></div>${chart(series)}${legend(['paired_ET','paired_RF'])}${gold?'<div class="legend"><span><i></i>公开档案实测</span></div>':''}<p class="data-note">直接评分模型输出整体Q，不生成用量曲线。横轴为实际加入量。</p></section>
    <section class="explanation"><h2>这份建议从哪里来？</h2><p>${esc(reason(i))}</p><div class="rank-composition"><div class="pair">曲线预测名次<strong>${rankText(r.paired_ET[i])}</strong></div><span>+</span><div class="direct">直接评分名次<strong>${rankText(r.direct_Q_ET[i])}</strong></div><span>→</span><div class="fusion">融合名次值<strong>${rankText(r.equal_rank[i])}</strong></div></div><p>两路名次各占50%，融合名次值越小越优。</p><p><span class="pair">曲线预测 Q ${fmt(p.paired_q[i])}</span><br><span class="direct">直接预测 Q ${fmt(p.direct_q[i])}</span></p><p>Q取40个用量点中最高4点的平均相对发光表现。模型分歧提示需要关注的候选，不等于校准后的风险概率。</p><details class="method-details"><summary>结构与输入信息</summary><p>SMILES：${esc(m.smiles)}</p><p>用量范围：${fmt(p.dose_pmol[i][0]/1000,2)}—${fmt(p.dose_pmol[i].at(-1)/1000,2)} nmol，40个已测网格点。使用分子描述符与Morgan指纹。</p></details></section></div>`;
  }
  function candidateRows(query=''){
    const p=current();
    return p.orders.equal_rank.filter(i=>`${name(mol(i))} ${mol(i).label}`.toLowerCase().includes(query.toLowerCase())).map(i=>`<tr class="${p.selected.includes(i)?'highlight-row':''}"><td><button class="table-button" data-pick="${i}">${esc(name(mol(i)))}<br><small>${esc(mol(i).label)}</small></button></td><td class="pair">${rankText(p.ranks.paired_ET[i])}</td><td class="direct">${rankText(p.ranks.direct_Q_ET[i])}</td><td>${rankText(p.ranks.equal_rank[i])}</td><td>${p.selected.includes(i)?'本轮推荐':'备选'}</td></tr>`).join('') || '<tr><td colspan="5">没有匹配的候选。</td></tr>';
  }
  function results(){
    const p=current();
    return header(`优先测试这${job.budget}个候选`,'综合两路预测，为本轮实验安排测试优先级。',`<button class="button secondary" data-view="report">${icon('report')}导出建议</button>`)+
    `<div class="result-context"><strong>${modeName(job.mode)}已完成 · ${fmt(job.seconds,2)} 秒</strong><span>${esc(job.pool)} · 36个历史配体 → 18个候选 · 固定等权融合</span></div>
    <div class="recommendations">${p.selected.map((i,k)=>{const m=mol(i);return `<button class="candidate-card ${selected===i?'active':''}" data-pick="${i}" aria-pressed="${selected===i}"><div class="candidate-top"><strong>优先 ${String(k+1).padStart(2,'0')}</strong><span>${esc(m.label)}</span>${selected===i?'<span class="selected-indicator"></span>':''}</div><div class="structure" aria-hidden="true">${m.svg}</div><div class="candidate-name">${esc(name(m))}</div><div class="candidate-formula">${esc(m.formula)}</div><div class="mini-ranks"><span class="pair">曲线<b>${rankText(p.ranks.paired_ET[i])}</b></span><span class="direct">评分<b>${rankText(p.ranks.direct_Q_ET[i])}</b></span><span class="fusion">融合<b>${rankText(p.ranks.equal_rank[i])}</b></span></div></button>`;}).join('')}</div>
    <div id="detail">${detail()}</div><details class="table-section"><summary>比较全部18个候选</summary><div class="search-row"><input type="search" id="candidate-search" placeholder="搜索名称或配体编号" aria-label="搜索候选"></div><div class="table-scroll"><table><thead><tr><th>候选配体</th><th>曲线名次</th><th>直接名次</th><th>融合名次值</th><th>建议</th></tr></thead><tbody id="candidate-rows">${candidateRows()}</tbody></table></div></details>
    <div class="bottom-actions"><p>推荐已生成。接下来用历史实测结果检查这份名单。</p><button class="button primary" data-view="evidence">查看实测对照 ${icon('arrow')}</button></div>`;
  }
  function evidence(){
    const p=current();
    if(!truth)return header('这份推荐，实际表现如何？','先保留模型给出的建议，再揭晓公开档案中的实测答案。')+
      `<div class="reveal-intro"><section class="sealed-panel">${icon('lock','seal-icon')}<h2>推荐名单已经固定</h2><p>接下来显示的是历史实验数据。查看各策略在相同测试名额下选到了什么，再对照全部15组的整体结果。</p><button class="button primary" data-action="reveal" ${busy?'disabled':''}>${busy?'正在读取实测…':'揭晓实测结果'} ${icon('arrow')}</button>${error?`<p class="error" role="alert">${esc(error)}</p>`:''}</section><section><h2>本轮的${job.budget}个推荐</h2><ul class="sealed-list">${p.selected.map(i=>`<li><div class="structure" aria-hidden="true">${mol(i).svg}</div><div><strong>${esc(name(mol(i)))}</strong><p class="small">${esc(mol(i).label)}</p></div><span class="pending">实测待揭晓</span></li>`).join('')}</ul><p class="data-note">此流程是公开数据的回顾性验证，不是新开展的湿实验。</p></section></div>`;
    const all=evidenceScope==='all';
    const summary=Object.fromEntries(truth.summary.map(r=>[r.method,r]));
    const gain=(1-summary.equal_rank.AUR/summary.paired_RF.AUR)*100;
    const gainET=(1-summary.equal_rank.AUR/summary.paired_ET.AUR)*100;
    const metric=truth.metrics;
    const lines=MAIN_METHODS.map(k=>({color:META[k].color,main:k==='equal_rank',dots:true,points:[1,2,3,4,5].map(b=>[b,all?summary[k]['B'+b]:metric[k].curve[b-1]])}));
    return header('把建议放回实验结果中检验','当前候选池与整体结果分开显示，所有策略使用相同推荐名额。',`<button class="button secondary" data-view="report">${icon('report')}查看决策报告</button>`)+
      `<div class="evidence-top"><section class="evidence-lead"><h2>整体筛选差距缩小 <span class="number">${fmt(gain,1)}%</span></h2><p>相对固定预算成对RF基线，全部15组、推荐名额1—5下的平均差距。融合相对成对ET单模型进一步缩小 ${fmt(gainET,1)}%。</p><p>指更接近候选池中的最佳配体，不是材料发光强度增幅。</p></section><section class="explanation"><h2>本轮推荐的实际表现</h2><div class="stat-line"><div><strong>${fmt(metric.equal_rank.selected_best)}</strong><span>名单中最佳实测Q</span></div><div><strong>${fmt(metric.equal_rank.oracle_Q)}</strong><span>候选池最佳实测Q</span></div></div><p>当前是 ${esc(job.pool)}，推荐 ${job.budget} 个。单池结果不代表整体收益，可返回任务设置切换全部15组。</p></section></div>
      <div class="tab-buttons" role="group" aria-label="对照范围"><button class="${!all?'active':''}" data-scope="pool" aria-pressed="${!all}">当前候选池</button><button class="${all?'active':''}" data-scope="all" aria-pressed="${all}">全部15组汇总</button></div>
      <div class="evidence-grid"><section class="surface curve-panel"><div class="section-head"><div><h2>相同名额，能找到多好的候选？</h2><p>${all?'全部15组平均':'当前组 · 精确处理随机选择和并列名次'}</p></div></div>${chart(lines,{xLabel:'推荐名额 / 配体数',yLabel:'最佳实测 Q 的期望',domainX:[1,5]})}${legend(MAIN_METHODS)}</section>
      <section class="surface evidence-table"><h2>${all?'全部15组的整体表现':'各策略在本轮的表现'}</h2><div class="table-scroll"><table><thead><tr><th>策略</th><th>${all?'平均差距 ↓':'名单最好Q ↑'}</th><th>${all?'选3个的期望Q ↑':'同分期望Q ↑'}</th></tr></thead><tbody>${MAIN_METHODS.map(k=>`<tr class="${k==='equal_rank'?'highlight-row':''}"><td style="color:${META[k].color}">${META[k].name}</td><td>${fmt(all?summary[k].AUR:metric[k].selected_best,4)}</td><td>${fmt(all?summary[k].B3:metric[k].curve[job.budget-1],4)}</td></tr>`).join('')}</tbody></table></div><p class="data-note">${all?'筛选差距：推荐集合中最好Q与候选池最好Q的差，按预算1—5取平均，越低越好。':'名单使用固定seed 42展示一次选择；期望值计算并列名次的随机平均，两者可能不同。'}</p></section></div>
      <details class="table-section"><summary>查看各策略的具体名单和实测值</summary><div class="table-scroll"><table><thead><tr><th>策略</th><th>推荐候选</th><th>实测Q</th></tr></thead><tbody>${MAIN_METHODS.flatMap(k=>p.orders[k].slice(0,job.budget).map((i,j)=>`<tr><td>${j===0?META[k].name:''}</td><td>${esc(name(mol(i)))}</td><td>${fmt(truth.molecules.find(m=>m.index===p.test[i]).gold_Q)}</td></tr>`)).join('')}</tbody></table></div></details>
      <details class="method-details"><summary>比较口径与结果范围</summary><p>RF使用42维表示，两个ET使用42维描述符与Morgan指纹。完整方案对RF的收益包含表示、模型与排序规则变化；融合的增益由ET单模型对照说明。RF上界与均值在本轮结果相同，主图合并显示。</p><p>融合在推荐3个时的平均最好Q比成对ET低约0.36%，整体平均差距更小。15组共用90种配体，不是15次独立实验。此处未开展额外效果实验。</p></details><div class="bottom-actions"><p>结果与运行信息可以一起保存，供团队讨论。</p><button class="button primary" data-view="report">形成决策报告 ${icon('arrow')}</button></div>`;
  }
  function reportView(){
    const p=current();
    return header('把实验建议带回团队','保存候选名单和本次运行依据，作为实验安排与讨论的起点。')+
      `<div class="report-layout"><article class="report-paper"><div class="report-brand">Amadeus</div><h2>实验决策报告</h2><p class="report-meta">纳米晶发光优化 · ${esc(job.pool)}<br>${day(job.created_at)} · ${modeName(job.mode)} · ${fmt(job.seconds,2)}秒</p><h3>研究目标</h3><p>在18种候选配体中，优先选择${job.budget}种进行测试。结合40点用量响应预测与直接评分，寻找更好的发光表现。</p><h3>本轮优先名单</h3><div class="table-scroll"><table><thead><tr><th>优先级</th><th>候选</th><th>曲线预测Q</th><th>直接预测Q</th></tr></thead><tbody>${p.selected.map((i,k)=>`<tr><td>${k+1}</td><td>${esc(name(mol(i)))}<br><small>${esc(mol(i).label)}</small></td><td>${fmt(p.paired_q[i])}</td><td>${fmt(p.direct_q[i])}</td></tr>`).join('')}</tbody></table></div><h3>推荐依据</h3>${p.selected.map(i=>`<p><strong>${esc(mol(i).label)}</strong>：${esc(reason(i))}</p>`).join('')}<h3>方法与复核</h3><p>两路名次各占50%，并列使用固定seed 42。训练配体与候选身份隔离。候选实测不参与本次预测与排序。Q是最高4个用量点的平均相对发光指标。</p>${truth?`<h3>已揭晓的历史对照</h3><p>本轮名单中最佳实测Q为${fmt(truth.metrics.equal_rank.selected_best)}，候选池最佳Q为${fmt(truth.metrics.equal_rank.oracle_Q)}。完整验证表可通过运行JSON导出。</p>`:''}<h3>下一步实验讨论</h3><p>结合配体可获得性、用量范围与实际实验条件确认测试安排。当前输出提供优先级；不会把预测最优点自动当作已验证的实验条件。</p></article>
      <aside class="surface export-panel"><h2>保存这次研究</h2><p>报告包含名单、两路预测与用量曲线。运行数据保留完整数值，方便复核。</p><button class="button primary full" data-action="report-export">${icon('report')}打开完整报告</button><button class="button secondary full" data-action="csv-export">${icon('download')}下载候选 CSV</button><button class="button secondary full" data-action="json-export">${icon('download')}下载运行 JSON</button><small>完整报告可打印或保存为PDF。</small><div class="report-id">RUN ${esc(job.id)}<br>${esc(job.created_at)}</div></aside></div>`;
  }
  async function loadHistory(){
    if(local)history=await api('/api/history');
    else{try{history=JSON.parse(localStorage.getItem('amadeus-history')||'[]');}catch{history=[];}}
  }
  function historyView(){
    return header('运行记录','回到已有任务，查看建议或重新导出结果。',`<button class="button primary" data-view="setup">新建分析 ${icon('arrow')}</button>`)+
      (history.length?`<div class="history-list">${history.map(h=>`<article class="history-row"><div class="case-icon">${icon('report')}</div><div class="history-info"><h2>纳米晶发光优化 · 推荐${h.budget}个</h2><p>${esc(h.pool)} · ${day(h.created_at)} · ${h.status==='complete'?'已完成':h.status==='failed'?'运行未完成':'运行中'}</p></div><span class="history-mode">${modeName(h.mode)}</span><button class="button secondary" data-open="${esc(h.id)}" ${h.status!=='complete'?'disabled':''}>打开记录 ${icon('arrow')}</button></article>`).join('')}</div>`:'<section class="surface empty"><h2>从第一个研究任务开始</h2><p>每次完成的分析都会保存在这里。</p><button class="button primary" data-view="setup">打开示例项目</button></section>');
  }
  function render(){
    navigation();
    $('main').innerHTML=({setup,running,results,evidence,report:reportView,history:historyView}[view])();
  }
  function midrank(values){return values.map(v=>1+values.filter(x=>x>v).length+(values.filter(x=>x===v).length-1)/2);}
  async function run(){
    if(busy)return;
    busy=true;truth=null;error='';
    job={stage:0,message:'准备任务与输入',status:'running'};
    view='running';render();
    try{
      if(local){
        const answer=await api('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pool:poolId,budget,mode})});
        while(true){
          job=await api(`/api/jobs/${answer.id}`);
          if(job.status==='complete')break;
          if(job.status==='failed')throw new Error(job.message);
          render();
          await new Promise(resolve=>setTimeout(resolve,700));
        }
      }else{
        const start=performance.now(),p=archive.pools.find(x=>x.id===poolId);
        const ranks={...p.ranks,paired_ET:midrank(p.paired_q),direct_Q_ET:midrank(p.direct_q)};
        ranks.equal_rank=ranks.paired_ET.map((v,i)=>(v+ranks.direct_Q_ET[i])/2);
        // Frozen order supplies the exact existing seed-42 tiebreaker; fresh ranks determine priority.
        const orders=Object.fromEntries(Object.keys(ranks).map(k=>[k,[...p.orders[k]].sort((a,b)=>ranks[k][a]-ranks[k][b])]));
        const result={...p,ranks,orders,selected:orders.equal_rank.slice(0,budget)};
        delete result.metrics;
        job={id:`web-${Date.now().toString(36)}`,pool:poolId,budget,mode:'replay',status:'complete',stage:3,
          created_at:new Date().toISOString(),seconds:(performance.now()-start)/1000,result};
        try{history.unshift({...job});history=history.slice(0,10);localStorage.setItem('amadeus-history',JSON.stringify(history));}catch{toast('浏览器未能保存记录，仍可导出本次结果。');}
      }
      selected=job.result.selected[0];evidenceScope='pool';busy=false;
      navigate('results');
    }catch(exc){busy=false;view='setup';error=exc.message;render();}
  }
  async function revealTruth(){
    if(busy)return;
    busy=true;render();
    try{
      if(local)truth=await api(`/api/jobs/${job.id}/reveal`);
      else{
        const p=archive.pools.find(x=>x.id===job.pool);
        truth={molecules:p.test.map(i=>({index:i,gold_Q:archive.molecules[i].gold_Q,gold_curve:archive.molecules[i].gold_curve})),
          metrics:Object.fromEntries(Object.entries(p.metrics).map(([k,v])=>[k,{...v,selected_best:Math.max(...job.result.orders[k].slice(0,job.budget).map(i=>archive.molecules[p.test[i]].gold_Q))}])),
          summary:archive.summary,comparisons:archive.comparisons};
      }
      error='';
    }catch(exc){error=exc.message;}
    busy=false;render();
  }
  function download(filename,content,type){
    const url=URL.createObjectURL(new Blob([content],{type}));
    const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);
  }
  function exportCSV(){
    if(local){const a=document.createElement('a');a.href=`/api/jobs/${job.id}/csv`;a.download=`amadeus-${job.id}.csv`;a.click();return;}
    const p=current();const rows=[['priority','label','name','paired_Q','direct_Q','paired_rank','direct_rank','fusion_rank_value'],...p.selected.map((i,k)=>[k+1,mol(i).label,name(mol(i)),p.paired_q[i],p.direct_q[i],p.ranks.paired_ET[i],p.ranks.direct_Q_ET[i],p.ranks.equal_rank[i]])];
    const quoted=v=>'"'+String(typeof v==='string'&&/^[=+@-]/.test(v)?"'"+v:v).replace(/"/g,'""')+'"';
    download(`amadeus-${job.id}.csv`,'\ufeff'+rows.map(r=>r.map(quoted).join(',')).join('\r\n'),'text/csv;charset=utf-8');
  }
  function exportReport(){
    if(local){window.open(`/api/jobs/${job.id}/report${truth?'?measured=1':''}`,'_blank','noopener');return;}
    const p=current();
    const article=document.querySelector('.report-paper').outerHTML;
    const curves=p.selected.map(i=>`<section><h2>${esc(name(mol(i)))}</h2>${chart([{color:'#32679d',points:p.paired_curves[i].map((v,j)=>[p.dose_pmol[i][j]/1000,v])}])}</section>`).join('');
    const content=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Amadeus · 实验决策报告</title><style>body{font:14px/1.8 system-ui,sans-serif;color:#203c34;max-width:900px;margin:40px auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}h2{margin-top:28px}section{break-inside:avoid}.chart{max-width:600px}.chart text{font-size:10px;fill:#65756c}.grid{stroke:#e1e8df}@media print{button{display:none}}</style><button onclick="window.print()">打印 / 保存为 PDF</button>${article}${curves}<p>运行 ${esc(job.id)} · 历史回放。数据来源：Kim et al., ACS Nano 2024, DOI 10.1021/acsnano.4c02094。</p></html>`;
    const url=URL.createObjectURL(new Blob([content],{type:'text/html;charset=utf-8'}));window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);
  }
  document.addEventListener('click',async e=>{
    const button=e.target.closest('button');if(!button||button.disabled)return;
    try{
      if(button.dataset.view){if(button.dataset.view==='history')await loadHistory();navigate(button.dataset.view);return;}
      if(button.dataset.budget){budget=Number(button.dataset.budget);render();return;}
      if(button.dataset.mode){mode=button.dataset.mode;render();return;}
      if(button.dataset.scope){evidenceScope=button.dataset.scope;render();return;}
      if(button.dataset.pick!==undefined){selected=Number(button.dataset.pick);if(button.closest('.candidate-card')){render();document.querySelector(`.candidate-card[data-pick="${selected}"]`)?.focus({preventScroll:true});}else{$('detail').innerHTML=detail();$('detail').scrollIntoView({behavior:'smooth',block:'start'});}return;}
      if(button.dataset.open){
        job=local?await api(`/api/jobs/${button.dataset.open}`):history.find(h=>h.id===button.dataset.open);
        poolId=job.pool;budget=job.budget;mode=job.mode;truth=null;selected=job.result.selected[0];navigate('results');return;
      }
      switch(button.dataset.action){
        case 'run':await run();break;
        case 'reveal':await revealTruth();break;
        case 'history':await loadHistory();navigate('history');break;
        case 'about':$('about').showModal();break;
        case 'close-about':$('about').close();break;
        case 'report-export':exportReport();break;
        case 'csv-export':exportCSV();break;
        case 'json-export':download(`amadeus-${job.id}.json`,JSON.stringify({...job,...(truth?{validation:truth}:{})},null,2),'application/json');break;
      }
    }catch(exc){toast(exc.message || '操作未完成，请重试。');}
  });
  document.addEventListener('change',e=>{if(e.target.id==='pool'){poolId=e.target.value;if(!basePool().live)mode='replay';else if(local)mode='live';render();}});
  document.addEventListener('input',e=>{if(e.target.id==='candidate-search')$('candidate-rows').innerHTML=candidateRows(e.target.value);});
  async function init(){
    try{
      if(['127.0.0.1','localhost'].includes(location.hostname)){
        try{C=await api('/api/catalog');local=Boolean(C.local);}catch{local=false;}
      }
      if(!local){
        const response=await fetch('./replay.json');if(!response.ok)throw new Error('演示数据未找到，请使用启动脚本或完整网站目录。');archive=await response.json();
        C={molecules:archive.molecules.map(({gold_Q,gold_curve,...m})=>m),pools:archive.pools.map(p=>({id:p.id,test:p.test,test_count:p.test.length,train_count:p.train.length,live:false})),default_pool:archive.default_pool};mode='replay';
      }
      poolId=C.default_pool;render();
    }catch(exc){$('main').innerHTML=`<div class="loading-view"><h1>工作台暂未就绪</h1><div class="error" role="alert">${esc(exc.message)}</div><p>请在项目目录运行 ./run_amadeus.sh，再打开终端显示的地址。</p></div>`;}
  }
  init();
})();
