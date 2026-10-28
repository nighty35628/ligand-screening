"use strict";
(() => {
  const D = JSON.parse(document.getElementById('demo-data').textContent);
  const $ = id => document.getElementById(id);
  const METHODS = D.methods;
  const META = {
    random:{name:'随机选择',color:'#697269',description:'无模型；均匀随机选择候选'},
    paired_RF:{name:'成对 RF · 均值',color:'#775578',description:'42 维结构描述符＋用量，按预测 Q 排序'},
    paired_RF_CI:{name:'成对 RF · 上界',color:'#80631f',description:'同一 RF，加入参照预测的不确定性'},
    paired_ET:{name:'成对 ET',color:'#245c9f',description:'预测用量曲线，再计算 Q'},
    direct_Q_ET:{name:'直接评分 ET',color:'#a14a18',description:'从配体表示直接预测 Q'},
    equal_rank:{name:'等权排名融合',color:'#246447',description:'两路名次各占 50%'}
  };
  let pool = D.pools.find(p => p.id === D.default_pool), budget = D.default_budget;
  let selected = pool.orders.equal_rank[0], revealed = false;
  const fmt = (x,n=3) => Number(x).toFixed(n);
  const rank = x => Number.isInteger(x) ? String(x) : fmt(x,2).replace(/0$/,'');
  const esc = x => String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const mol = local => D.molecules[pool.test[local]];
  const name = m => m.name===m.smiles ? `配体 ${m.label}` : m.name;
  const best = method => Math.max(...pool.orders[method].slice(0,budget).map(i=>mol(i).gold_Q));
  $('pool-select').innerHTML = D.pools.map(p=>`<option value="${p.id}">划分 ${p.replicate+1} / 第 ${p.fold+1} 折 · ${p.id}</option>`).join('');
  $('pool-select').value = pool.id;
  $('budget-select').value = budget;
  function chart(series,{xLabel,yLabel,height=220,xTicks=5,yTicks=4,domainX=null,domainY=null}={}) {
    const w=520,h=height,l=54,r=16,t=19,b=44;
    const points=series.flatMap(s=>s.points).filter(p=>p.every(Number.isFinite));
    let [xmin,xmax]=domainX || [Math.min(...points.map(p=>p[0])),Math.max(...points.map(p=>p[0]))];
    let [ymin,ymax]=domainY || [Math.min(0,...points.map(p=>p[1])),Math.max(...points.map(p=>p[1]))*1.08];
    if(ymax===ymin)ymax=ymin+1;if(xmax===xmin)xmax=xmin+1;
    const x=v=>l+(v-xmin)/(xmax-xmin)*(w-l-r),y=v=>h-b-(v-ymin)/(ymax-ymin)*(h-b-t);
    let svg=`<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(yLabel)}随${esc(xLabel)}变化"><title>${esc(yLabel)}与${esc(xLabel)}</title>`;
    for(let i=0;i<=yTicks;i++){const v=ymin+(ymax-ymin)*i/yTicks;svg+=`<line class="grid" x1="${l}" y1="${y(v)}" x2="${w-r}" y2="${y(v)}"/><text text-anchor="end" x="${l-9}" y="${y(v)+4}">${fmt(v,1)}</text>`;}
    for(let i=0;i<xTicks;i++){const v=xmin+(xmax-xmin)*i/(xTicks-1);svg+=`<text text-anchor="middle" x="${x(v)}" y="${h-b+20}">${Number(v.toFixed(2))}</text>`;}
    svg+=`<text x="${l}" y="12">${esc(yLabel)}</text><text text-anchor="middle" x="${(w+l-r)/2}" y="${h-4}">${esc(xLabel)}</text>`;
    series.forEach(s=>{svg+=`<polyline fill="none" stroke="${s.color}" stroke-width="2.4" ${s.dash?'stroke-dasharray="6 4"':''} stroke-linejoin="round" points="${s.points.map(p=>`${x(p[0])},${y(p[1])}`).join(' ')}"/>`;if(s.dots)s.points.forEach(p=>svg+=`<circle cx="${x(p[0])}" cy="${y(p[1])}" r="3" fill="${s.color}"/>`);});
    return svg+'</svg>';
  }
  function renderCandidates(){
    $('candidate-rows').innerHTML=pool.orders.equal_rank.map(i=>{
      const m=mol(i);return `<tr class="${i===selected?'selected':''}" data-candidate="${i}"><td><button class="ligand-pick" data-pick="${i}" aria-pressed="${i===selected}" aria-label="查看 ${esc(name(m))}"><span class="molecule-thumb" aria-hidden="true">${m.svg}</span><span class="ligand-label">${esc(name(m))}<small>${esc(m.label)}</small></span></button></td><td class="pair-color num">${rank(pool.ranks.paired_ET[i])}</td><td class="direct-color num">${rank(pool.ranks.direct_Q_ET[i])}</td><td class="fusion-color num"><strong>${rank(pool.ranks.equal_rank[i])}</strong></td><td class="num">${revealed?`<span data-truth>${fmt(m.gold_Q)}</span>`:'<span class="sealed">待揭晓</span>'}</td></tr>`;
    }).join('');
  }
  function renderDetail(){
    const i=selected,m=mol(i),pa=pool.ranks.paired_ET[i],di=pool.ranks.direct_Q_ET[i];
    const series=[{color:META.paired_RF.color,dash:true,points:pool.rf_curves[i].map((v,j)=>[pool.dose_pmol[i][j]/1000,v])},{color:META.paired_ET.color,dash:true,points:pool.paired_curves[i].map((v,j)=>[pool.dose_pmol[i][j]/1000,v])}];
    if(revealed)series.push({color:'#202923',points:m.gold_curve.map((v,j)=>[pool.dose_pmol[i][j]/1000,v])});
    $('ligand-detail').innerHTML=`<div class="detail-label"><span>${esc(m.label)} · 选中配体</span><span>固定池中的第 ${i+1} 个档案</span></div><h3>${esc(name(m))}</h3><div class="formula">${esc(m.formula)}</div><div class="molecule-main" role="img" aria-label="${esc(name(m))} 的二维化学结构">${m.svg}</div><div class="model-paths"><div><div class="path-head pair-color">A · 成对 ET</div><p class="path-explain">参考配体 → 40 点用量曲线 → Q</p><div class="pred-number pair-color">${fmt(pool.paired_q[i])}<small>预测 Q</small></div><div class="rank-line">本池名次 <strong>${rank(pa)}</strong> / 18</div></div><div><div class="path-head direct-color">B · 直接评分 ET</div><p class="path-explain">配体表示 → 直接预测 Q</p><div class="pred-number direct-color">${fmt(pool.direct_q[i])}<small>预测 Q</small></div><div class="rank-line">本池名次 <strong>${rank(di)}</strong> / 18</div></div></div><div class="fusion-equation"><strong>融合名次值 ${rank(pool.ranks.equal_rank[i])}</strong><span>(${rank(pa)} + ${rank(di)}) ÷ 2 · 越小越优</span></div><p class="chart-title">用量—发光响应</p>${chart(series,{xLabel:'配体用量 / nmol（线性坐标）',yLabel:'相对发光指标 FOM'})}<div class="legend"><span class="pred" style="color:${META.paired_RF.color}">成对 RF 预测</span><span class="pred pair-color">成对 ET 预测</span>${revealed?'<span data-truth>公开档案实测</span>':''}</div><p class="small">直接模型只输出一个 Q 分数，不预测用量曲线。</p><p class="truth-line">${revealed?`实测 Q <strong class="num" data-truth>${fmt(m.gold_Q)}</strong>`:'实测 Q <span class="sealed">待揭晓</span>'}</p><details><summary>查看结构标识</summary><p>SMILES：${esc(m.smiles)}</p><p>InChI：${esc(m.id)}</p></details>`;
  }
  function renderStrategies(){
    $('budget-caption').textContent=`每种策略都选 ${budget} 个，严格计入预算`;
    $('strategy-grid').innerHTML=METHODS.map(method=>`<article class="strategy" data-method="${method}" style="--strategy:${META[method].color}"><h3 style="color:${META[method].color}">${META[method].name}</h3><p>${META[method].description}</p><ol class="chosen-list">${pool.orders[method].slice(0,budget).map((i,k)=>`<li data-selected="${pool.test[i]}"><span class="position">${k+1}.</span><button data-pick="${i}">${esc(name(mol(i)))}</button><span class="chosen-score num">${revealed?`<span data-truth>${fmt(mol(i).gold_Q)}</span>`:'<span class="sealed">待揭晓</span>'}</span></li>`).join('')}</ol><div class="strategy-result"><span>这次选择中，最好的实测 Q</span><strong class="num">${revealed?`<span data-truth>${fmt(best(method))}</span>`:'—'}</strong><small>${revealed?`平局随机期望：${fmt(pool.metrics[method].curve[budget-1])}`:'揭晓后显示 · 同分使用固定 seed 42'}</small></div></article>`).join('');
  }
  function renderOverview(){
    const sums=Object.fromEntries(D.summary.map(s=>[s.method,s]));
    const gain=m=>(1-sums.equal_rank.AUR/sums[m].AUR)*100;
    const cmp=m=>D.comparisons.find(c=>c.baseline===m);
    const plotted=['random','paired_RF','paired_ET','direct_Q_ET','equal_rank'];
    const series=plotted.map(m=>({color:META[m].color,dots:true,points:[1,2,3,4,5].map(b=>[b,sums[m]['B'+b]])}));
    $('overview').innerHTML=`<div class="section-title"><h2><span>整体结果：更早接近候选池中的好配体</span></h2><span>全部 15 池 · 固定预算 1—5</span></div><div class="overview-grid"><div><p class="overview-lead">融合的平均筛选差距比成对 RF 缩小 <strong>${fmt(gain('paired_RF'),1)}%</strong>，比成对 ET 单独使用缩小 <strong>${fmt(gain('paired_ET'),1)}%</strong>。</p><p class="small">筛选差距是推荐集中最好配体与本池最好配体之间的 Q 差；数值越低越好。这里的百分比不代表材料发光增幅。</p><table class="summary-table overview-table"><caption class="sr-only">统一比较的全部结果</caption><thead><tr><th>选择方法</th><th>平均差距 ↓</th><th>选 3 个后最好 Q ↑</th></tr></thead><tbody>${METHODS.map(m=>`<tr data-summary="${m}"><td style="color:${META[m].color}">${META[m].name}</td><td class="num">${fmt(sums[m].AUR,4)}</td><td class="num">${fmt(sums[m].B3,4)}</td></tr>`).join('')}</tbody></table></div><div><h3>相同推荐名额，能选到多好的配体？</h3>${chart(series,{xLabel:'推荐预算 / 配体数',yLabel:'平均最佳实测 Q ↑',xTicks:5,domainX:[1,5],domainY:[1.1,2.05]})}<div class="legend">${plotted.map(m=>`<span style="color:${META[m].color}">${META[m].name}</span>`).join('')}</div><p class="small">RF 的均值与上界规则在本轮预算 1—5 的结果相同，图中合并显示。15 池来自 3 套五折划分，共用 90 种配体。</p></div></div><details class="result-details"><summary>查看稳定性与适用范围</summary><p>融合对 RF：${cmp('paired_RF').wins_ties_losses.join(' / ')} 池胜／平／负；对成对 ET：${cmp('paired_ET').wins_ties_losses.join(' / ')}。融合在预算 3 时，平均最好 Q 相对成对 ET 为 ${fmt((sums.equal_rank.B3/sums.paired_ET.B3-1)*100,2)}%。</p><p>RF 使用 42 维描述符，ET 使用描述符＋Morgan。相对 RF 的变化包含表示、模型与排序策略；融合本身的收益由两个 ET 单模型对照解释。RF 为固定计算预算实现。全部结果是同一公开档案的回顾性评估，未新增湿实验或独立盲测。</p></details>`;
  }
  function renderOutcomes(){
    $('reveal-state').textContent=revealed?'已揭晓 · 现有档案答案':'本池实测答案尚未显示';
    if(!revealed){$('outcomes').innerHTML='<div class="hidden-panel"><p>先比较六份推荐名单，再揭晓它们在公开实测档案中的表现。</p><button class="primary" data-reveal>揭晓实测结果 ↗</button></div>';return;}
    const displayed=['random','paired_RF','paired_ET','direct_Q_ET','equal_rank'];
    const series=displayed.map(m=>({color:META[m].color,dots:true,points:pool.metrics[m].curve.map((v,j)=>[j+1,v])}));
    $('outcomes').innerHTML=`<div class="outcome-grid"><div><h3>当前候选池：推荐更多，结果如何变化？</h3>${chart(series,{xLabel:'推荐预算 / 配体数',yLabel:'最佳实测 Q 的期望',xTicks:5,domainX:[1,5]})}<div class="legend">${displayed.map(m=>`<span style="color:${META[m].color}">${META[m].name}</span>`).join('')}</div></div><div><h3>${esc(pool.id)} · 本池对照</h3><p>本池最优实测 Q：<strong class="num">${fmt(pool.metrics.equal_rank.oracle_Q)}</strong>。正式评分对随机选择与并列名次计算精确期望。</p><table class="summary-table"><thead><tr><th>方法</th><th>预算 ${budget}：最好 Q ↑</th><th>平均差距 ↓</th></tr></thead><tbody>${METHODS.map(m=>`<tr data-pool-metric="${m}"><td>${META[m].name}</td><td class="num">${fmt(pool.metrics[m].curve[budget-1],4)}</td><td class="num">${fmt(pool.metrics[m].AUR,4)}</td></tr>`).join('')}</tbody></table></div></div><div class="scope-note">上方名单使用固定 seed 42 展示一次选择；表格与曲线使用精确随机期望，两者可能不同。切换候选池可查看全部情况，不以单池输赢判断整体效果。</div>`;
  }
  function render(){
    $('pool-context').textContent=`${pool.train.length} 个训练配体 → ${pool.test.length} 个候选`;
    $('status').textContent=revealed?`已揭晓 ${pool.id} 的公开实测结果；可换池查看不同情况，或重新隐藏答案。`:`${pool.id} · 预算 ${budget} 个配体 · 实测暂时隐藏。点击候选可查看两路模型为什么给出不同排名。`;
    $('reveal-button').innerHTML=revealed?'重新隐藏实测 <span aria-hidden="true">↺</span>':'揭晓实测结果 <span aria-hidden="true">↗</span>';
    renderCandidates();renderDetail();renderStrategies();renderOutcomes();
  }
  function reveal(){revealed=true;render();}
  $('pool-select').addEventListener('change',e=>{pool=D.pools.find(p=>p.id===e.target.value);selected=pool.orders.equal_rank[0];revealed=false;render();document.querySelector('.table-scroll').scrollTop=0;});
  $('budget-select').addEventListener('change',e=>{budget=Number(e.target.value);revealed=false;render();});
  $('reveal-button').addEventListener('click',()=>{revealed=!revealed;render();});
  document.addEventListener('click',e=>{const pick=e.target.closest('[data-pick]');if(pick){const fromStrategy=Boolean(pick.closest('.strategy'));selected=Number(pick.dataset.pick);renderCandidates();renderDetail();if(fromStrategy){$('prediction').setAttribute('tabindex','-1');$('prediction').focus({preventScroll:true});$('prediction').scrollIntoView({behavior:'smooth',block:'start'});}else{document.querySelector(`#candidate-rows [data-pick="${selected}"]`).focus({preventScroll:true});}}if(e.target.closest('[data-reveal]'))reveal();});
  $('provenance').innerHTML=`<p>数据：ALLiS 公开实测档案，固定仓库提交 1796d18496c669d554fa165a88d83e7b3cd9a905；90 种完整配体，每种 40 个用量点。原始来源和资源归属保留在本地 provenance 与协议文件中。</p><p>Q：40 个用量点最高 4 个相对 PL FOM 的平均，不是绝对 PLQY。实际用量以 pmol 输入；图中换算为 nmol，不推断自由配体浓度或表面覆盖度。</p><p>本轮：${D.execution.new_fits} 次 RF 拟合，模型保存后加载预测；两个 ET 组件复用已核验的历史预测，另有单池重训验收。RF 与成对 ET 都使用固定 131072 个训练对、48 棵树、depth 16、leaf 2；直接 ET 为 256 棵树。无本轮寻参，融合固定为两路中间名次各占 50%。</p><p>RF 上界为参照预测均值加 t 系数乘标准误，参照预测并非独立测量，不能视作校准置信区间。本地统一评估 ${D.verification.rows} 条方法／候选池记录，独立复算通过。</p><p>本页为离线结果回放，数据文件含既有答案；隐藏与揭晓只服务讲解。没有现场训练、连续用量优化或多轮反馈实验。本轮基线是固定预算下的候选推荐比较，不代表完整自动实验流程的复现。</p>`;
  renderOverview();
  render();
})();
