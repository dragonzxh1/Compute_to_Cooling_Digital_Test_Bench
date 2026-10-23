// Document rendering from saved/authored JSON only. No hydraulic computation.
export function renderNetwork(spec){
 const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 const pos={RETURN_HEADER:[70,600],SUPPLY_HEADER:[1730,600]};
 for(const [s,y] of [['A',170],['B',390]]){
  spec.nodes.filter(n=>n.startsWith('CDU_'+s+':')).forEach((n,i)=>pos[n]=[200+i*140,y]);
 }
 for(let i=1;i<=6;i++){
  const r='R'+String(i).padStart(2,'0'),y=690+(i-1)*105;pos[r+':IN']=[1200,y];pos[r+':OUT']=[700,y];
 }
 if(Object.keys(pos).length!==spec.nodes.length)throw Error('UNPLACED_JSON_NODE');
 const names={pipe:'管段',pump:'泵',check_valve:'止回',filter:'过滤器',heat_exchanger:'板换',isolation_valve:'隔离阀',motor_valve:'选择阀',rack:'机柜'};
 let links='',nodes='',labels='';
 for(const e of spec.edges){
  const [x1,y1]=pos[e.from],[x2,y2]=pos[e.to];let d;
  if(y1===y2)d=`M${x1},${y1}H${x2}`;
  else if(e.from==='RETURN_HEADER'||e.from==='SUPPLY_HEADER')d=`M${x1},${y1}V${y2}H${x2}`;
  else d=`M${x1},${y1}H${x2}V${y2}`;
  const color=e.kind==='pump'?'#fbbf24':e.budget==='RACK'?'#34d399':'#22d3ee';
  links+=`<path data-edge="${esc(e.id)}" d="${d}" fill="none" stroke="${color}" stroke-width="2" marker-end="url(#arrow)"/>`;
  const tx=(x1+x2)/2,ty=y1===y2?y1:y1===600?y2:y1;
  labels+=`<text x="${tx}" y="${ty-27}" text-anchor="middle" class="tiny">${esc(e.id)} · ${names[e.kind]||esc(e.kind)}</text><text x="${tx}" y="${ty-10}" text-anchor="middle" class="tiny">${e.kind==='pump'?'研究Q-H':Number(e.design_drop_kPa).toFixed(2)+' kPa'}</text>`;
 }
 for(const n of spec.nodes){
  const [x,y]=pos[n];nodes+=`<circle cx="${x}" cy="${y}" r="5" fill="#0f172a" stroke="#a78bfa" stroke-width="2"/>`;
  let label=n.replace('CDU_A:','A/').replace('CDU_B:','B/');
  if(n==='RETURN_HEADER')label='回液母管';if(n==='SUPPLY_HEADER')label='供液母管';
  nodes+=`<text x="${x}" y="${y+24}" text-anchor="middle" class="tiny">${esc(label)}</text>`;
 }
 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1800 1450" role="img" aria-label="JSON逐边约简水力网络，不是施工图"><defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#1e293b" stroke-width="0.5"/></pattern><marker id="arrow" markerWidth="8" markerHeight="7" refX="7" refY="3.5" orient="auto"><path d="M0 0L8 3.5L0 7Z" fill="#94a3b8"/></marker></defs><style>text{font-family:'Cascadia Code','Microsoft YaHei','Noto Sans SC',sans-serif;fill:#e2e8f0;font-size:18px}.tiny{font-size:11px;fill:#cbd5e1}</style><rect width="100%" height="100%" fill="#0f172a"/><rect width="100%" height="100%" fill="url(#grid)"/><rect x="115" y="95" width="1560" height="155" rx="12" fill="none" stroke="#a78bfa" stroke-dasharray="8 4"/><rect x="115" y="315" width="1560" height="155" rx="12" fill="none" stroke="#a78bfa" stroke-dasharray="8 4"/>${links}${labels}${nodes}<text x="140" y="125">CDU A · 单泵/单过滤支路约简</text><text x="140" y="345">CDU B · 单泵/单过滤支路约简</text><text x="50" y="40" style="font-size:27px;font-weight:700">00/01 · 36节点 / 42连接 · 单六柜水力预算模型</text><text x="50" y="72" class="tiny">由02号JSON逐边生成；所有可建模路径的模板，不代表A/B同时运行许可；缺失的另一100%内部支路不在此图内。</text><rect x="150" y="1305" width="1500" height="105" rx="10" fill="#351c2d" stroke="#fb7185"/><text x="180" y="1335">真实定压 / 补液 / 膨胀 / 标高 / 泄压：OPEN · 表压不可确定</text><text x="180" y="1362" class="tiny">本图只表示二次介质回路。一次介质只与HX热耦合、不直接混合；源侧与负荷侧由客户储罐解耦，但本阶段未动态建模。</text><text x="180" y="1387" class="tiny">研究拆分不是OEM曲线；准稳态模型无水锤/闭锁压力/热响应。不是施工P&amp;ID，不得用于采购或施工。</text></svg>`;
}
