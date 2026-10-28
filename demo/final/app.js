'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const D = JSON.parse($('demo-data').textContent);
  const ICON = {
    arrow:'<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    down:'<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    check:'<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m4 10 4 4 8-8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };
  const META={random:{name:'随机选择',color:'#697269'},paired_RF:{name:'成对 RF',color:'#78617e'},paired_RF_CI:{name:'RF 上界排序',color:'#78617e'},paired_ET:{name:'成对 ET',color:'#315f91'},direct_Q_ET:{name:'评分 ET',color:'#9b532f'},equal_rank:{name:'双模型融合',color:'#245c46'}};
  const DISPLAY=['random','paired_RF','paired_ET','direct_Q_ET','equal_rank'];
  const steps=['准备筛选','查看推荐','揭晓实测','效果对比'];
  const state={screen:'setup',pool:D.pools.find(p=>p.id===D.default_pool),budget:D.default_budget,selected:0,order:null,reached:0,scope:'all',token:0,fast:false};
  const fmt=(x,n=3)=>Number(x).toFixed(n);
  const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rank=x=>Number.isInteger(x)?String(x):fmt(x,2).replace(/0$/,'');
  const mol=i=>D.molecules[state.pool.test[i]];
  const name=m=>m.name===m.smiles?`配体 ${m.label}`:m.name;
  const chosen=()=>state.order.slice(0,state.budget);
  const activeStep=()=>({setup:0,analyzing:0,recommended:1,revealing:2,measured:2,compare:3}[state.screen]);
  const busy=()=>['analyzing','revealing'].includes(state.screen);
  const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  const announce=text=>{$('live-status').textContent=text;};
  function focusStage(){requestAnimationFrame(()=>{const h=$('stage').querySelector('h1');if(h){h.tabIndex=-1;h.focus({preventScroll:true});}window.scrollTo({top:0,behavior:'instant'});});}
  function renderStepper(){
    const current=activeStep();
    $('stepper').innerHTML=steps.map((label,i)=>`${i?`<span class="step-line ${i<=current?'done':''}" aria-hidden="true"></span>`:''}<button class="step-item ${i<current?'done':''}" data-step="${i}" ${i===current?'aria-current="step"':''} ${busy()||i>state.reached?'disabled':''}><span class="step-number">${i+1}</span>${label}</button>`).join('');
  }
  function preview(){
    return `<div class="preview-sheet"><div class="sheet-head"><strong>本轮候选档案</strong><span>${state.pool.test.length} 种配体</span></div><div class="specimen-grid">${[0,1,2,3].map(i=>`<div class="specimen"><div class="molecule-preview" aria-hidden="true">${mol(i).svg}</div><div class="specimen-name"><span>${esc(mol(i).label)}</span><span>${esc(mol(i).formula)}</span></div></div>`).join('')}</div><div class="sheet-foot"><i aria-hidden="true"></i>结构与用量信息已就绪</div></div>`;
  }
  function renderSetup(){
    $('stage').innerHTML=`<div class="screen setup"><div class="setup-copy"><h1>下一轮，<br>先测哪几个配体？</h1><p class="subtitle">从分子结构与用量响应中寻找线索，为钙钛矿纳米晶挑选优先测试的配体。</p><div class="config"><div><label for="pool-select" class="field-label">选择候选组</label><div class="select-wrap"><select id="pool-select">${D.pools.map((p,i)=>`<option value="${p.id}" ${p.id===state.pool.id?'selected':''}>候选组 ${String(i+1).padStart(2,'0')} · ${p.test.length} 种配体</option>`).join('')}</select>${ICON.down}</div></div><div><span class="field-label" id="budget-label">这一轮，准备测试几个？</span><div class="budget-options" role="group" aria-labelledby="budget-label">${[1,2,3,4,5].map(n=>`<button class="budget-option" data-budget="${n}" aria-pressed="${n===state.budget}">${n} 个</button>`).join('')}</div></div></div><div class="setup-actions"><button class="primary" id="start-analysis">开始筛选 ${ICON.arrow}</button><span class="small">${state.pool.train.length} 种历史配体作参考</span></div></div><div id="preview">${preview()}</div></div>`;
  }
  function chart(series,{xLabel='配体用量 / nmol',yLabel='相对发光 FOM',height=220,xTicks=4,domainX=null}={}){
    const w=530,h=height,l=43,r=15,t=28,b=43;
    const points=series.flatMap(s=>s.points).filter(p=>p.every(Number.isFinite));
    let [xmin,xmax]=domainX||[Math.min(...points.map(p=>p[0])),Math.max(...points.map(p=>p[0]))];
    const ymin=Math.min(0,...points.map(p=>p[1]));let ymax=Math.max(...points.map(p=>p[1]))*1.12;
    if(ymax<=ymin)ymax=ymin+1;if(xmax<=xmin)xmax=xmin+1;
    const x=v=>l+(v-xmin)/(xmax-xmin)*(w-l-r),y=v=>h-b-(v-ymin)/(ymax-ymin)*(h-b-t);
    let svg=`<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(yLabel)}随${esc(xLabel)}变化"><title>${esc(yLabel)}随${esc(xLabel)}变化</title>`;
    for(let k=0;k<4;k++){const v=ymin+(ymax-ymin)*k/3;svg+=`<line class="grid" x1="${l}" y1="${y(v)}" x2="${w-r}" y2="${y(v)}"/><text x="${l-8}" y="${y(v)+4}" text-anchor="end">${fmt(v,1)}</text>`;}
    for(let k=0;k<xTicks;k++){const v=xmin+(xmax-xmin)*k/(xTicks-1);svg+=`<text x="${x(v)}" y="${h-b+20}" text-anchor="middle">${Number(v.toFixed(1))}</text>`;}
    svg+=`<text x="${l}" y="14">${esc(yLabel)}</text><text x="${(w+l-r)/2}" y="${h-3}" text-anchor="middle">${esc(xLabel)}</text>`;
    for(const s of series){svg+=`<polyline fill="none" stroke="${s.color}" stroke-width="${s.emphasis?2.7:1.8}" stroke-linejoin="round" ${s.dash?'stroke-dasharray="5 4"':''} points="${s.points.map(p=>`${x(p[0])},${y(p[1])}`).join(' ')}"/>`;if(s.dots)for(const p of s.points)svg+=`<circle cx="${x(p[0])}" cy="${y(p[1])}" r="${s.emphasis?3.4:2.5}" fill="${s.color}"><title>${esc(s.name||'')}: ${p[0]} / ${fmt(p[1])}</title></circle>`;}
    return svg+'</svg>';
  }
  function detail(measured){
    const p=state.pool,i=state.selected,m=mol(i);
    const series=[{color:META.paired_ET.color,dash:true,points:p.paired_curves[i].map((v,j)=>[p.dose_pmol[i][j]/1000,v])}];
    if(measured)series.push({color:'#245c46',emphasis:true,points:m.gold_curve.map((v,j)=>[p.dose_pmol[i][j]/1000,v])});
    return `<div class="detail-sheet"><div class="detail-heading"><div><h2>${esc(name(m))}</h2><p class="small">${esc(m.formula)}</p></div><span class="detail-label">${esc(m.label)}</span></div><div class="molecule-large" role="img" aria-label="${esc(name(m))}的分子结构">${m.svg}</div><div class="prediction-summary"><div><span>曲线模型预测 Q</span><strong class="pair-color" data-predicted="paired">${fmt(p.paired_q[i])}</strong><small>本组名次 ${rank(p.ranks.paired_ET[i])}</small></div><div><span>评分模型预测 Q</span><strong class="direct-color" data-predicted="direct">${fmt(p.direct_q[i])}</strong><small>本组名次 ${rank(p.ranks.direct_Q_ET[i])}</small></div><div><span>${measured?'实测 Q':'融合名次值'}</span><strong class="fusion-color" ${measured?'data-truth':''}>${measured?fmt(m.gold_Q):rank(p.ranks.equal_rank[i])}</strong><small>${measured?'来自公开实验档案':'两路名次各占 50%'}</small></div></div><div class="curve-heading"><h3>用量与发光响应</h3><div class="legend"><span class="dashed pair-color"><i></i>预测</span>${measured?'<span class="fusion-color"><i></i>实测</span>':''}</div></div>${chart(series)}<details class="identity"><summary>结构标识</summary><p>SMILES：${esc(m.smiles)}</p><p>InChI：${esc(m.id)}</p></details></div>`;
  }
  function candidateTable(measured){
    return `<details class="all-candidates"><summary>浏览全部 ${state.pool.test.length} 个候选</summary><div class="candidate-scroll"><table class="candidate-table"><caption class="sr-only">全体候选排名</caption><thead><tr><th>配体</th><th>曲线</th><th>评分</th><th>融合</th>${measured?'<th>实测 Q</th>':''}</tr></thead><tbody>${state.order.map(i=>`<tr class="${i===state.selected?'active':''}"><td><button data-pick="${i}">${esc(mol(i).label)}</button></td><td>${rank(state.pool.ranks.paired_ET[i])}</td><td>${rank(state.pool.ranks.direct_Q_ET[i])}</td><td>${rank(state.pool.ranks.equal_rank[i])}</td>${measured?`<td data-truth>${fmt(mol(i).gold_Q)}</td>`:''}</tr>`).join('')}</tbody></table></div></details>`;
  }
  function renderRecommendation(measured=false){
    const picks=chosen();
    const best=measured?Math.max(...picks.map(i=>mol(i).gold_Q)):null;
    $('stage').innerHTML=`<div class="screen"><div class="stage-top"><div><h1>${measured?'这一轮，选到了什么？':`名单就绪，先看这 ${state.budget} 个。`}</h1><p>候选组 ${String(D.pools.indexOf(state.pool)+1).padStart(2,'0')} · 从 ${state.pool.test.length} 种配体中推荐 ${state.budget} 种</p></div><div class="stage-actions"><button class="primary" id="${measured?'show-comparison':'reveal-results'}">${measured?'查看效果对比':'揭晓实测结果'} ${ICON.arrow}</button><button class="text-button" data-reset>重新选择</button></div></div><div class="recommend-grid"><div>${measured?`<div class="measured-summary"><div><span>本次推荐中最好 Q</span><strong data-truth>${fmt(best)}</strong></div><div><span>本组全部候选最好 Q</span><strong data-truth>${fmt(state.pool.metrics.equal_rank.oracle_Q)}</strong></div></div>`:''}<div class="recommend-list">${picks.map((i,k)=>`<button class="recommend-pick" data-pick="${i}" data-selected="${state.pool.test[i]}" aria-pressed="${i===state.selected}"><span class="pick-index">${String(k+1).padStart(2,'0')}</span><span class="pick-molecule" aria-hidden="true">${mol(i).svg}</span><span class="pick-name">${esc(name(mol(i)))}<span class="pick-meta">${esc(mol(i).formula)} · 融合名次值 ${rank(state.pool.ranks.equal_rank[i])}</span>${measured?`<span class="pick-gold">实测 Q<strong data-truth>${fmt(mol(i).gold_Q)}</strong></span>`:''}</span></button>`).join('')}</div><p class="selection-caption">${measured?'点击配体，对照预测与实测曲线。':'点击配体，查看两路判断与用量曲线。'}</p>${candidateTable(measured)}</div><section id="ligand-detail" aria-label="配体详情">${detail(measured)}</section></div></div>`;
  }
  function renderComparison(){
    const global=state.scope==='all';
    const sums=global?Object.fromEntries(D.summary.map(r=>[r.method,r])):state.pool.metrics;
    const base=sums.paired_RF.AUR,ours=sums.equal_rank.AUR;
    const gain=base>1e-12?(base-ours)/base*100:null;
    const insight=gain===null?`融合的平均筛选差距为 <strong>${fmt(ours,4)}</strong>`:`平均筛选差距<br>比成对 RF ${gain>=0?'缩小':'增加'} <strong>${fmt(Math.abs(gain),1)}%</strong>`;
    const series=DISPLAY.map(m=>({name:META[m].name,color:META[m].color,emphasis:m==='equal_rank',dots:true,points:[1,2,3,4,5].map(b=>[b,sums[m]['B'+b]])}));
    const metricRow=m=>`<tr data-summary="${m}" class="${m==='equal_rank'?'ours':''}"><td>${META[m].name}</td><td>${fmt(sums[m].AUR,4)}</td><td>${fmt(sums[m].B3,4)}</td></tr>`;
    const c=D.comparisons.find(c=>c.baseline==='paired_ET');
    $('stage').innerHTML=`<div class="screen"><div class="stage-top"><div><h1>把这次选择，放进对照里。</h1><p>${global?'全部 15 个固定候选组':'当前候选组'} · 相同推荐预算，比较筛选结果</p></div><div class="stage-actions"><button class="secondary" data-reset>再筛选一组 ${ICON.arrow}</button></div></div><div class="compare-scope" role="group" aria-label="对比范围"><button class="scope-option" data-scope="all" aria-pressed="${global}">全部 15 组</button><button class="scope-option" data-scope="pool" aria-pressed="${!global}">当前候选组</button></div><div class="comparison-grid"><div class="comparison-plot"><h2>多一个名额，能选到多好？</h2>${chart(series,{xLabel:'推荐预算 / 配体数',yLabel:'最佳实测 Q ↑',height:285,xTicks:5,domainX:[1,5]})}<div class="legend">${DISPLAY.map(m=>`<span style="color:${META[m].color}"><i></i>${META[m].name}</span>`).join('')}</div></div><div class="comparison-findings"><h2>${insight}</h2><p>筛选差距是推荐中最好 Q 与候选池最优 Q 的差距，越小越好。</p><table class="metrics-table"><caption class="sr-only">${global?'全部候选组':'当前组'}方法比较</caption><thead><tr><th>选择方法</th><th>平均差距 ↓</th><th>推荐 3 个<br>最好 Q ↑</th></tr></thead><tbody>${DISPLAY.map(metricRow).join('')}</tbody></table><details class="comparison-extra"><summary>完整对照与稳定性</summary>${global?`<p>融合对成对 ET 的平均差距缩小 ${fmt((1-sums.equal_rank.AUR/sums.paired_ET.AUR)*100,1)}%；15组中 ${c.wins_ties_losses[0]} 胜、${c.wins_ties_losses[1]} 平、${c.wins_ties_losses[2]} 负。预算3时，最好Q相对成对ET为 ${fmt((sums.equal_rank.B3/sums.paired_ET.B3-1)*100,2)}%。</p>`:'<p>单组表现可能高于或低于总体。切换“全部15组”查看总体结果。</p>'}<table class="metrics-table"><thead><tr><th>补充规则</th><th>平均差距 ↓</th><th>推荐 3 个最好 Q ↑</th></tr></thead><tbody>${metricRow('paired_RF_CI')}</tbody></table><p>对比使用平局随机期望，与上一页固定名单的单次结果可能不同。百分比是筛选差距的变化，不是材料发光增幅。</p></details></div></div><div class="comparison-foot"><p>结果来自已有实验档案，可切换全部候选组复核。</p><button class="text-button" data-step="2">返回本轮实测</button></div></div>`;
  }
  function render(){renderStepper();if(state.screen==='setup')renderSetup();else if(state.screen==='recommended')renderRecommendation();else if(state.screen==='measured')renderRecommendation(true);else if(state.screen==='compare')renderComparison();$('stage').setAttribute('aria-busy',String(busy()));}
  function reset(){state.token++;state.screen='setup';state.reached=0;state.order=null;state.fast=false;render();focusStage();announce('已返回设置，结果已隐藏。');}
  function midrank(values){return values.map(v=>1+values.filter(x=>x>v).length+(values.filter(x=>x===v).length-1)/2);}
  function calculateRanking(){
    const p=state.pool;
    if(p.paired_q.length!==18||p.direct_q.length!==18||![...p.paired_q,...p.direct_q].every(Number.isFinite))throw Error('候选预测数据不完整');
    const a=midrank(p.paired_q),b=midrank(p.direct_q),f=a.map((v,i)=>(v+b[i])/2);
    for(let i=0;i<18;i++)if(f[i]!==p.ranks.equal_rank[i])throw Error('融合排名与核验记录不一致');
    const fixedTie=new Map(p.orders.equal_rank.map((v,i)=>[v,i]));
    state.order=f.map((_,i)=>i).sort((i,j)=>f[i]-f[j]||fixedTie.get(i)-fixedTie.get(j));
    state.selected=state.order[0];
  }
  function progressScreen(reveal,labels){
    $('stage').innerHTML=`<div class="screen processing ${reveal?'reveal-process':''}"><div class="processing-molecule" aria-hidden="true">${mol(reveal?state.selected:0).svg}<div class="scan-sweep"></div></div><h1>${reveal?'让实测结果来回答。':'把线索，整理成下一步。'}</h1><p class="subtitle">${reveal?'正在调取这一组配体的公开实验记录。':'两路模型各作判断，再合成一份推荐名单。'}</p><div class="progress-head"><span id="progress-label">${labels[0]}</span><span id="progress-percent" class="num">0%</span></div><div class="progress-track" id="analysis-progress" role="progressbar" aria-label="演示进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div id="progress-fill" class="progress-fill"></div></div><div class="progress-stages" id="progress-stages">${labels.map((label,i)=>`<div data-progress-step="${i}">${label}</div>`).join('')}</div><div class="progress-actions"><button class="text-button" id="skip-progress">直接查看</button><button class="text-button" id="cancel-progress">取消</button></div></div>`;
  }
  function progressTo(start,end,duration,token){
    return new Promise(resolve=>{
      const since=performance.now();
      function tick(now){
        if(state.token!==token){resolve(false);return;}
        const t=state.fast||reduced()?1:Math.min(1,(now-since)/duration);
        const value=start+(end-start)*(1-Math.pow(1-t,2));
        $('progress-fill').style.transform=`scaleX(${value/100})`;
        $('progress-percent').textContent=`${Math.floor(value)}%`;
        $('analysis-progress').setAttribute('aria-valuenow',String(Math.floor(value)));
        if(t>=1)resolve(true);else requestAnimationFrame(tick);
      }requestAnimationFrame(tick);
    });
  }
  async function process(reveal=false){
    if(busy())return;
    const token=++state.token;state.fast=false;state.screen=reveal?'revealing':'analyzing';renderStepper();
    const labels=reveal?['匹配实验档案','读取实测曲线','对照推荐名单']:['读取候选结构','载入模型预测','融合候选排名','整理推荐名单'];
    progressScreen(reveal,labels);$('stage').setAttribute('aria-busy','true');focusStage();
    try{
      for(let k=0;k<labels.length;k++){
        if(state.token!==token)return;
        $('progress-label').textContent=labels[k];announce(labels[k]);
        document.querySelectorAll('[data-progress-step]').forEach((el,i)=>{el.className=i<k?'done':i===k?'active':'';el.innerHTML=(i<k?ICON.check:'')+labels[i];});
        if(!reveal&&k===2)calculateRanking();
        if(reveal&&k===1)for(const i of chosen())if(!Number.isFinite(mol(i).gold_Q)||mol(i).gold_curve.length!==40)throw Error('实测档案不完整');
        if(!await progressTo(k/labels.length*100,(k+1)/labels.length*100,reveal?470:800,token))return;
      }
      if(state.token!==token)return;
      state.screen=reveal?'measured':'recommended';state.reached=Math.max(state.reached,reveal?2:1);render();focusStage();announce(reveal?'实测结果已揭晓。':'推荐名单已生成。');
    }catch(error){
      state.token++;state.screen='error';$('stage').setAttribute('aria-busy','false');
      $('stage').innerHTML=`<div class="error-state"><h1>这次读取没有完成</h1><p>${esc(error.message)}。可以返回重新开始。</p><button class="primary" data-reset>返回设置</button></div>`;announce('读取失败，请返回设置。');focusStage();
    }
  }
  $('methods-toggle').addEventListener('click',()=>{const open=$('methods').hidden;$('methods').hidden=!open;$('methods-toggle').setAttribute('aria-expanded',String(open));if(open)$('methods').scrollIntoView({behavior:reduced()?'instant':'smooth',block:'start'});});
  document.addEventListener('change',e=>{if(e.target.id==='pool-select'){state.pool=D.pools.find(p=>p.id===e.target.value);state.order=null;$('preview').innerHTML=preview();}});
  document.addEventListener('click',e=>{
    const button=e.target.closest('button');if(!button||button.disabled)return;
    if(button.dataset.budget){state.budget=Number(button.dataset.budget);document.querySelectorAll('[data-budget]').forEach(el=>el.setAttribute('aria-pressed',String(Number(el.dataset.budget)===state.budget)));}
    if(button.id==='start-analysis')process();
    if(button.id==='reveal-results')process(true);
    if(button.id==='skip-progress')state.fast=true;
    if(button.id==='cancel-progress'||button.hasAttribute('data-reset'))reset();
    if(button.id==='show-comparison'){state.screen='compare';state.reached=3;render();focusStage();}
    if(button.dataset.scope){state.scope=button.dataset.scope;renderComparison();document.querySelector(`[data-scope="${state.scope}"]`).focus({preventScroll:true});}
    if(button.hasAttribute('data-step')&&!busy()){
      const step=Number(button.dataset.step);if(step>state.reached)return;
      if(step===0){reset();return;}state.screen=['setup','recommended','measured','compare'][step];render();focusStage();
    }
    if(button.hasAttribute('data-pick')){
      state.selected=Number(button.dataset.pick);
      $('ligand-detail').innerHTML=detail(state.screen==='measured');
      document.querySelectorAll('.recommend-pick').forEach(el=>el.setAttribute('aria-pressed',String(Number(el.dataset.pick)===state.selected)));
      document.querySelectorAll('.candidate-table tr').forEach(el=>{const b=el.querySelector('[data-pick]');if(b)el.classList.toggle('active',Number(b.dataset.pick)===state.selected);});
    }
  });
  render();
})();
