"use strict";
(() => {
  const D = JSON.parse(document.getElementById('demo-data').textContent);
  const $ = id => document.getElementById(id);
  const METHODS = ['paired_ET','direct_Q_ET','equal_rank'];
  const META = {
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
      const m=mol(i);return `<tr class="${i===selected?'selected':''}" data-candidate="${i}"><td><button class="ligand-pick" data-pick="${i}" aria-pressed="${i===selected}" aria-label="查看 ${esc(m.name)}"><span class="molecule-thumb" aria-hidden="true">${m.svg}</span><span class="ligand-label">${esc(m.name)}<small>${esc(m.label)}</small></span></button></td><td class="pair-color num">${rank(pool.ranks.paired_ET[i])}</td><td class="direct-color num">${rank(pool.ranks.direct_Q_ET[i])}</td><td class="fusion-color num"><strong>${rank(pool.ranks.equal_rank[i])}</strong></td><td class="num">${revealed?`<span data-truth>${fmt(m.gold_Q)}</span>`:'<span class="sealed">待揭晓</span>'}</td></tr>`;
    }).join('');
  }
  function renderDetail(){
    const i=selected,m=mol(i),pa=pool.ranks.paired_ET[i],di=pool.ranks.direct_Q_ET[i];
    const series=[{color:META.paired_ET.color,dash:true,points:pool.paired_curves[i].map((v,j)=>[pool.dose_pmol[i][j]/1000,v])}];
    if(revealed)series.push({color:'#202923',points:m.gold_curve.map((v,j)=>[pool.dose_pmol[i][j]/1000,v])});
    $('ligand-detail').innerHTML=`<div class="detail-label"><span>${esc(m.label)} · 选中配体</span><span>固定池中的第 ${i+1} 个档案</span></div><h3>${esc(m.name)}</h3><div class="formula">${esc(m.formula)}</div><div class="molecule-main" role="img" aria-label="${esc(m.name)} 的二维化学结构">${m.svg}</div><div class="model-paths"><div><div class="path-head pair-color">A · 成对 ET</div><p class="path-explain">参考配体 → 40 点用量曲线 → Q</p><div class="pred-number pair-color">${fmt(pool.paired_q[i])}<small>预测 Q</small></div><div class="rank-line">本池名次 <strong>${rank(pa)}</strong> / 18</div></div><div><div class="path-head direct-color">B · 直接评分 ET</div><p class="path-explain">配体表示 → 直接预测 Q</p><div class="pred-number direct-color">${fmt(pool.direct_q[i])}<small>预测 Q</small></div><div class="rank-line">本池名次 <strong>${rank(di)}</strong> / 18</div></div></div><div class="fusion-equation"><strong>融合名次值 ${rank(pool.ranks.equal_rank[i])}</strong><span>(${rank(pa)} + ${rank(di)}) ÷ 2 · 越小越优</span></div><p class="chart-title">用量—发光响应</p>${chart(series,{xLabel:'配体用量 / nmol（线性坐标）',yLabel:'相对发光指标 FOM'})}<div class="legend"><span class="pred pair-color">成对模型预测</span>${revealed?'<span data-truth>公开档案实测</span>':''}</div><p class="small">直接模型只输出一个 Q 分数，不预测用量曲线。</p><p class="truth-line">${revealed?`实测 Q <strong class="num" data-truth>${fmt(m.gold_Q)}</strong>`:'实测 Q <span class="sealed">待揭晓</span>'}</p><details><summary>查看结构标识</summary><p>SMILES：${esc(m.smiles)}</p><p>InChI：${esc(m.id)}</p></details>`;
  }
  function renderStrategies(){
    $('budget-caption').textContent=`每种策略都选 ${budget} 个，严格计入预算`;
    $('strategy-grid').innerHTML=METHODS.map(method=>`<article class="strategy" data-method="${method}" style="--strategy:${META[method].color}"><h3 style="color:${META[method].color}">${META[method].name}</h3><p>${META[method].description}</p><ol class="chosen-list">${pool.orders[method].slice(0,budget).map((i,k)=>`<li data-selected="${pool.test[i]}"><span class="position">${k+1}.</span><button data-pick="${i}">${esc(mol(i).name)}</button><span class="chosen-score num">${revealed?`<span data-truth>${fmt(mol(i).gold_Q)}</span>`:'<span class="sealed">待揭晓</span>'}</span></li>`).join('')}</ol><div class="strategy-result"><span>这次选择中，最好的实测 Q</span><strong class="num">${revealed?`<span data-truth>${fmt(best(method))}</span>`:'—'}</strong><small>${revealed?`平局随机期望：${fmt(pool.metrics[method].curve[budget-1])}`:'揭晓后显示 · 同分使用固定 seed 42'}</small></div></article>`).join('');
  }
  function renderOutcomes(){
    $('reveal-state').textContent=revealed?'已揭晓 · 现有档案答案':'实测答案尚未显示';
    if(!revealed){$('outcomes').innerHTML='<div class="hidden-panel"><p>先比较三份推荐名单，再揭晓它们在公开实测档案中的表现。</p><button class="primary" data-reveal>揭晓实测结果 ↗</button></div>';return;}
    const qcurves=METHODS.map(method=>({color:META[method].color,dots:true,points:pool.metrics[method].curve.map((v,j)=>[j+1,v])}));
    const sums=Object.fromEntries(D.summary.map(s=>[s.method,s]));
    const gain=(1-sums.equal_rank.AUR/sums.paired_ET.AUR)*100;
    const b3=(sums.equal_rank.B3/sums.paired_ET.B3-1)*100;
    const b5=(sums.equal_rank.B5/sums.paired_ET.B5-1)*100;
    $('outcomes').innerHTML=`<div class="outcome-grid"><div><h3>当前候选池：多测几个，能选到多好？</h3><p>纵轴为所选候选中最佳实测 Q 的平局随机期望，越高越好。不是固定 seed 42 的单次抽签结果。</p>${chart(qcurves,{xLabel:'测试预算 / 配体数',yLabel:'最佳实测 Q 的期望',xTicks:5,domainX:[1,5],domainY:[Math.max(0,Math.min(...qcurves.flatMap(s=>s.points.map(p=>p[1])))-.10),Math.max(...qcurves.flatMap(s=>s.points.map(p=>p[1])))*1.03]})}<div class="legend">${METHODS.map(m=>`<span style="color:${META[m].color}">${META[m].name}</span>`).join('')}</div><p>本池最优配体的实测 Q：<strong class="num">${fmt(pool.metrics.equal_rank.oracle_Q)}</strong>。三种方法都只看预测再选择，实测仅用于回放评分。</p></div><div><h3>全部 15 个固定池：看整体，也保留代价</h3><p>AUR 是预算 1—5 下，距本池最优 Q 的平均差距，越低越好；B3 是选 3 个后最佳实测 Q 的期望。15 池来自 3 次划分×5 折，并非 15 组独立实验。</p><table class="summary-table"><caption class="sr-only">全部固定池汇总</caption><thead><tr><th>策略</th><th>AUR ↓</th><th>B3：最佳 Q ↑</th></tr></thead><tbody>${METHODS.map(m=>`<tr><td style="color:${META[m].color}">${META[m].name}</td><td class="num">${fmt(sums[m].AUR,4)}</td><td class="num">${fmt(sums[m].B3,4)}</td></tr>`).join('')}</tbody></table><p class="finding">融合的平均差距相对成对 ET 缩小 <strong>${fmt(gain,1)}%</strong>；预算 3 时最佳 Q 平均 <strong>${fmt(b3,2)}%</strong>，预算 5 时 <strong>${fmt(b5,2)}%</strong>。</p><p>融合对成对模型：4 池更好、6 池持平、5 池更差。提升集中在部分池，不能解释为“材料发光提升 12.4%”。</p></div></div><div class="scope-note">固定 seed 42 名单方便讲解；正式对照对同分候选取精确随机期望，因此两种数值可能不同。本轮是回顾性证据，未新增湿实验或独立盲测；原先要求 B3 不退化的严格替换门槛未通过。</div>`;
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
  $('provenance').innerHTML=`<p>数据：ALLiS 公开实测档案 reaction_collection_train_AL0503.json；固定原仓库提交 1796d18496c669d554fa165a88d83e7b3cd9a905。90 个配体，每个 40 个用量点；每池训练 36 个、留出 18 个。这里展示全部候选池，不按结果选择展示池。</p><p>预测：outputs/allis_retrain_verified（30 次既有拟合），数据封印与 verification.json 已由导出脚本核验。本演示新增拟合次数：0。</p><p>输入：原 42 维表示＋计数 Morgan（radius 2，2048 维）。成对 ET：48 树，depth 16，leaf 2，131072 个对称训练对；直接评分 ET：256 树，leaf 2。成对模型用量输入仍为线性 pmol；图中仅将单位换算为 nmol。</p><p>两路预测均按分数从高到低转名次，同分取平均名次；融合仅计算两路名次均值。推荐同分用 seed 42；汇总评分取同分的精确均匀随机期望。15 个池不是独立重现实验，不据此宣称统计显著。</p><p>离线文件内已包含既有答案，“隐藏”只服务讲解，不构成新的独立测试。manifest.json 可核对来源和页面哈希。</p>`;
  render();
})();
