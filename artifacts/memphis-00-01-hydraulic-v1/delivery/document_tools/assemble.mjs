// Independent SAVED-EVIDENCE arithmetic and document generation only.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import readline from 'node:readline';
import {renderNetwork} from './diagram.mjs';
const run=process.argv[2], repo=path.resolve(import.meta.dirname,'../..');
const root=`D:/Github/c2c-evidence-review/memphis-00-01-hydraulic-v1/run${run}`;
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const byte=read(path.join(root,'independent_byte_review.json'));
const raw=path.join(byte.official_root,`artifacts/memphis-00-01-hydraulic-v1/${run}-1/baseline/delivery`);
const result=read(path.join(raw,'stage_result.json'));
const dest=path.join(root,'reviewed-delivery');fs.mkdirSync(dest,{recursive:true});
const write=(n,s)=>fs.writeFileSync(path.join(dest,n),s,{flag:'wx'});
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const basis=read(path.join(repo,'v0_2/tests/tools/memphis_00_01_hydraulic_v1/basis.json'));
const spec=read(path.join(raw,'02_HYDRAULIC_NETWORK_NETLIST.json'));
const curves=[];let frames=0,maxMass=0,maxPower=0,maxEquation=0;
for(const c of result.cases){
 const series=[];
 for await(const line of readline.createInterface({input:fs.createReadStream(path.join(raw,c.case+'.ndjson')),crlfDelay:Infinity})){
  const {row,network:n}=JSON.parse(line),b=Array(spec.nodes.length).fill(0);let hyd=0,friction=0;
  if(Object.values(n.physical_gauge_kPa).some(x=>x!==null)||row.permission!==false)throw Error('FALSE_PHYSICAL_PRESSURE_OR_PERMISSION');
  for(const e of n.edges){const q=e.flow_m3_s;b[e.i]+=q;b[e.j]-=q;
   if(e.kind==='pump')hyd-=q*e.pressure_drop_Pa;else friction+=q*e.pressure_drop_Pa;
   if(q>1e-8||!['pump','check_valve'].includes(e.kind)){
    const expected=e.kind==='pump'||e.kind==='check_valve'?e.k*q*q-e.head:(()=>{const s=e.k*q*q;return q*Math.sqrt(.5*e.k*(s+Math.sqrt(s*s+.04)))})();
    maxEquation=Math.max(maxEquation,Math.abs(expected-e.pressure_drop_Pa));
   }
  }
  maxMass=Math.max(maxMass,...b.map(Math.abs));maxPower=Math.max(maxPower,Math.abs(hyd-friction));
  series.push(row);frames++;
 }
 if(series.length!==600)throw Error('TRACE_LENGTH');
 const z=series.slice(100).filter(r=>r.min_rack_flow_m3_h<.001).length*.1;
 const deficit=series.slice(100).reduce((s,r)=>s+Math.max(0,68.37-r.unit_flow_m3_h)*.1/3600,0);
 if(Math.abs(z-c.zero_flow_duration_s)>1e-7||Math.abs(deficit-c.deficit_m3)>1e-9)throw Error('RESULT_NOT_SUPPORTED_BY_TRACE');
 curves.push({case:c.case,rows:series,result:c});
}
if(maxMass>1e-8||maxPower>.01||maxEquation>.001)throw Error('INDEPENDENT_CONSERVATION_OR_EDGE_EQUATION');
const independent={frames,maxMass_m3_s:maxMass,maxPower_W:maxPower,maxEquation_Pa:maxEquation,scope:'Saved hydraulic equations only, NOT thermal/field calibration',pressure_nulls_verified:true};
for(const f of fs.readdirSync(raw))fs.copyFileSync(path.join(raw,f),path.join(dest,f),fs.constants.COPYFILE_EXCL);
write('independent_trace_review.json',JSON.stringify(independent,null,2));
write('independent_byte_review.json',JSON.stringify(byte,null,2));
fs.cpSync(path.join(repo,'v0_2/tests/tools/memphis_00_01_hydraulic_v1'),path.join(dest,'source'),{recursive:true,errorOnExist:true});
const provenance=`# 00/01 来源与边界\n\n只以00/01原件为设计权威。两份DOCX本轮重新读取并验证RAW SHA256；B编号为word/document.xml顶层body元素编号，不是印刷页码。\n\n${basis.sources.map(s=>`- ${s.filename}: ${s.raw_sha256}`).join('\n')}\n\n00 B154/B158：源侧96.52、负荷侧155.92 kPa分别由罐解耦，不相加为一台泵扬程。B163：二次371.81 kPa。B165/B168：真实顺序为回液→泵→过滤器→板换→供液；B167集中压降等效表不是逐个真实接口压力。\n\nB146：板换两侧入口表压差≤10kPa，所有泵入口≥50kPag。B168：定压实施仍待落实。335.89/60kPag为示例，未当作真实定压装置。\n\nR12仅为过程拓扑参照。本阶段是36节点42边的约简水力预算模型，并非完整R12或客户竣工网络。分支内过滤器20、阀组30kPa与机柜选择阀各1kPa是研究拆分，不是厂家数据。\n\n计算方法参考：[EPA EPANET](https://www.epa.gov/water-research/epanet)，仅说明管网建模方法，不证明本项目设备性能。\n`;
write('03_PRESSURE_SOURCE_PROVENANCE.md',provenance);
const rfi=[['OEM-PUMP','CDU及源/负荷泵','各转速Q-H/效率/电机功率/NPSHR/关死扬程，指定PG25温度范围','原始厂家曲线+FAT实测点','覆盖0、设计Q、1.2Q；不接受单额定点替代曲线'],['OEM-HX','六台CDU板换','一次85.92@110、二次26.60@68.37压降曲线；污垢UA；单侧与跨侧结构允许值','四口压力测点位置与厂家性能面','10kPa运行要求不得替代结构耐压'],['OEM-VALVE','选择/隔离/止回/过滤器','Kv/Cv-开度、动作/关闭时间、清洁/堵塞Δp-Q、方向和泄漏','设备位号对应的曲线与FAT','区分100%并联支路，禁止串联重复计损'],['DESIGN-PRESSURE','定压/补液/膨胀/泄压','一次二次实际接点、参考高程、预充/设定值、有效容积、泄压整定与排放能力','设计院签署回路图+厂家数据','证明正常/失泵/单侧失压时入口≥50和跨侧≤10；无资料保持OPEN'],['DESIGN-PIPE','实际管网','各段L/内径/材质粗糙度/局部K/标高/液体物性','与P&ID位号绑定的等轴图及设备表','123.58kPa只是等效预算，不可当竣工实测'],['SYSTEM-FAT-SAT','单六柜再到18柜','泵故障、压力主站交接、阀序、每柜温流压同步反馈','系统级高频原始轨迹+测量校准','组件FAT不等于整系统无断流；不得用命令代替反馈']];
const csv=v=>'"'+String(v??'').replaceAll('"','""')+'"';
write('13_OEM_DATA_REQUEST.csv','\uFEFF'+[['id','equipment','required_data','evidence','acceptance'],...rfi].map(r=>r.map(csv).join(',')).join('\r\n'));
const trip=result.cases.find(c=>c.case.endsWith('TRIP'));
const report=`# 00/01 水力网络与定压 V1：第一阶段交付\n\n结论：预算与约简网络可复验；实际定压边界尚未闭环。PHYSICAL_DESIGN_PASS = NO。不是完整00/01动态模型验收。\n\n执行commit ${byte.source_commit}；[远程运行](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/${run})。CPU允许100%分配容量（Job rate10000），进程4GiB/Job8GiB，480秒；仅单六柜两条60秒水力轨迹，没有运行热模型/18柜/1800秒。\n\n## 12项回答\n\n1. 预算：源侧57.62+18.90+20=96.52；负荷侧85.92+50+20=155.92；二次171.63+123.58+26.60+50=371.81 kPa，三者不能跨罐叠加。\n2. 这些为设计预算；真实管段几何、Kv、过滤器及泵/HX全曲线均未获校准。新模型逐边标明研究拆分，无一条被冒充OEM曲线。\n3. 旧研究模型一次HX130、二次172.18kPa与00/01不同，外部PIPE零阻力漏掉123.58kPa。旧192.412不是客户真实系统结论。\n4. 二次设计点68.37m³/h需371.81kPa；70m³/h/500kPa/22kW是候选额定点。三个相交于该额定点的研究Q-H族给出不同工作点/调速需求，不能选出唯一真实曲线。效率、实际电耗/泵热、NPSH仍OPEN。\n5. 旧B-CDU在30.5秒：P1=284.009489、P2=476.421825kPag；有符号差=(165−100)+(284.009489−165)−(476.421825−100)=−192.412336kPa。高程在旧模型为零假设，不是实测；泵及上游损失合成在局部动态项内，不能把该值外推客户方案。\n6. 同高程设计点示例P1=431.81，P2=Csec+371.81−Lpre，则≤10要求Csec在[50+Lpre,70+Lpre]kPag。与入口≥50可条件性共存，但60示例只在0≤Lpre≤10时成立；Lpre=50时差50kPa。真实吸入口位置、停泵闭锁压力和瞬态没有闭合，不能据此宣称全工况兼容或必然冲突。\n7. 需要带明确接点/标高/有效容积/预充及压力范围的定压、补液、膨胀和单侧泄压/保护设计。是否必须新增何种装置尚无证据，不凭空并入客户方案。\n8. 00/01提出压力要求并给等效压力示例，但未充分定义上述物理实现及标高，相关接口保留OPEN。\n9. 厂家数据及可验收交付格式见13号RFI；组件FAT、系统集成FAT/SAT分开。\n10. 受控T2在压力输入缺失时保持HOLD，未发生新旧泵实际交接，因此不能回答已成功消除交接缺口。独立突然失泵诊断：10秒后近零流量${trip.zero_flow_duration_s.toFixed(1)}秒，亏缺${trip.deficit_m3.toFixed(9)}m³。此为约简模型无储能/无备用已建流路径，不是客户真实停泵水锤或自动恢复验证。\n11. 证据支持优先核实现有备用泵、合法重叠、真实定压与接口。尚没有证明足以施工的最小新增设备候选，不能判定必须加第三回路或扩大RC。\n12. 未具备完整18柜动态验证放行条件；先补定压/OEM/逐段几何及单六柜热水力接口。不得把本阶段PASS当工程批准。\n\n## 放行门槛\n\nG1预算映射完成（约简模型、研究分配另列）；G2物理定压OPEN；G3条件性包络可复验但实际工作点OPEN；G4形成机制条件性明确、实际跨侧差压OPEN；G5吸入口/NPSH/承压OPEN；G6只完成短程水力诊断，热动态未验证；G7受控HOLD与突然失泵FAIL分开。整体NOT_READY。\n\n## 独立证据核验\n\n${frames}帧；最大节点质量残差${maxMass} m³/s；最大水力功率账差${maxPower}W；最大逐边方程残差${maxEquation}Pa。无温度结果、无热守恒PASS。数值锚点仅消除规范自由度；实际表压全部null，KCL小不等于压力唯一。止回阀只为准稳态互补，不含关闭时间。\n\n## 独立状态\n\n${Object.entries(result).filter(([k])=>k.endsWith('_STATUS')).map(([k,v])=>'- '+k+' = '+v).join('\n')}\n\n冻结M1/00/01原件/历史证据未修改；无正式C3-C、生产、硬件、采购或Phase6授权。\n`;
write('14_ENGINEERING_REPORT_ZH.md',report);
// SVG: every authored node and edge, with explicit reduced-model limitations.
const svg=renderNetwork(spec);
write('12_PHYSICAL_HYDRAULIC_PID.svg',svg);
const escaped=JSON.stringify(curves).replaceAll('<','\\u003c');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
write('15_INTERACTIVE_REPORT.html',`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>00/01 水力预算与定压 V1</title><style>body{margin:0;background:#f1f5f9;color:#17334b;font:16px/1.65 system-ui,'Microsoft YaHei',sans-serif}main{max-width:1200px;margin:auto;padding:32px}h1{font-size:30px}section{background:white;border:1px solid #dce5ee;border-radius:16px;padding:24px;margin:20px 0}.warn{background:#fff3df;border-left:5px solid #d98b21;padding:18px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.metric{padding:20px;background:#f4f8fb;border-radius:10px}.metric b{display:block;font-size:28px}select,input{font:inherit;width:100%;margin:12px 0}svg{width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.8 system-ui}a{color:#087b97}small{color:#547085}@media(max-width:650px){main{padding:16px}.grid{grid-template-columns:1fr}}</style><main><small>00/01唯一设计权威 · 单六柜约简水力模型</small><h1>先算清阻力，再谈真实压力</h1><div class="warn">工程未批准。实际表压不可确定；受控接管未放行。这里没有热仿真结果，也没有完成完整00/01动态网络验证。</div><section><h2>实际保存轨迹</h2><label for="case">诊断场景</label><select id="case"><option value="0">受控T2请求：压力边界缺失，保持HOLD</option><option value="1">突然失泵：独立连续供流失败</option></select><div class="grid"><div class="metric">当前时间<b id="time"></b></div><div class="metric">六柜总流量 m³/h<b id="flow"></b></div><div class="metric">实际表压<b>未确定</b></div></div><label for="tick">轨迹时间（0–59.9秒）</label><input id="tick" type="range" min="0" max="599" value="0"><svg id="plot" viewBox="0 0 1000 240" role="img" aria-label="六柜总流量曲线"></svg><p id="state"></p><small>全部数值由对应原始NDJSON生成；不存在命令即流量、HOLD即接管成功的判定。</small></section><section><h2>网络与未闭合接口</h2>${svg}</section><section><h2>工程结论及12项回答</h2><pre>${escape(report)}</pre></section><section><h2>原始证据入口</h2><a href="02_HYDRAULIC_NETWORK_NETLIST.json">网络JSON</a> · <a href="01_00_01_PRESSURE_BUDGET.csv">压力预算</a> · <a href="13_OEM_DATA_REQUEST.csv">厂家RFI</a> · <a href="16_SOURCE_AND_EVIDENCE_MANIFEST.json">哈希清单</a> · <a href="https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/${run}">远程run</a></section></main><script>const data=${escaped};const pick=document.getElementById('case'),tick=document.getElementById('tick');function draw(){const d=data[+pick.value],r=d.rows[+tick.value];document.getElementById('time').textContent=r.t_s.toFixed(1)+' s';document.getElementById('flow').textContent=r.unit_flow_m3_h.toFixed(3);document.getElementById('state').textContent=r.state+' · T2许可：否 · 压力条件：OPEN';const points=d.rows.map((v,i)=>(40+i/599*920)+','+(200-v.unit_flow_m3_h/80*160)).join(' ');document.getElementById('plot').innerHTML='<path d="M40 25V200H970" fill="none" stroke="#b4c5d2"/><line x1="40" y1="63.26" x2="960" y2="63.26" stroke="#cc7c2a" stroke-dasharray="6 5"/><polyline points="'+points+'" fill="none" stroke="#087e99" stroke-width="3"/><text x="45" y="20" fill="#547085">80 m³/h</text><text x="45" y="225" fill="#547085">0 s</text><text x="900" y="225" fill="#547085">59.9 s</text><text x="650" y="52" fill="#a46924">设计需求 68.37 m³/h</text>';};pick.onchange=draw;tick.oninput=draw;draw();</script></html>`);
const files=[];function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else files.push({path:path.relative(dest,p).replaceAll('\\','/'),bytes:fs.statSync(p).size,sha256:hash(fs.readFileSync(p))});}}walk(dest);
write('16_SOURCE_AND_EVIDENCE_MANIFEST.json',JSON.stringify({revision:'00-01-HYDRAULIC-V1-STAGE1',source_commit:byte.source_commit,official_zip_sha256:byte.official_zip_sha256,source_manifest_sha256:byte.source_manifest_sha256,self_excluded:true,records:files},null,2));
console.log(JSON.stringify({dest,independent,package_manifest_sha256:hash(fs.readFileSync(path.join(dest,'16_SOURCE_AND_EVIDENCE_MANIFEST.json')))}));
