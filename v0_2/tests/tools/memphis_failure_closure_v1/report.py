"""One source-bound engineering decision, component FAT and actual interactive traces."""
import json,html,os,hashlib
from pathlib import Path
from .requirements import save,csvout
from .checks import need
from .upstream_report import verified_inputs,plot
from .fat import rows as fat_rows
from .scenarios import trials
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finalize(directory):
    found,groups=verified_inputs();dynamic=[];tanks=[];locations={};prior=None;standby=None
    for name,(a,d) in found.items():
        if a['kind']=='prior':prior=a
        if a['kind']=='dynamic':
            for r in a['cases']:dynamic.append(r);locations[r['id']]=d/('case' if name=='G_WET_LOSS' else r['id']+'/case')
        if a['kind']=='tank':tanks+=a['cases']
        if a['kind']=='standby':standby=a
        if a['kind']=='analytic':
            save(directory/'minimum_performance_requirements.json',a['results'])
            for p in d.glob('*.csv'):(directory/p.name).write_bytes(p.read_bytes())
    expected=[c for s in json.loads((HERE/'registration.json').read_bytes())['cases'] if s['kind']=='bundle' for c in trials(s['study'])]
    need({r['id'] for r in dynamic}=={'G_WET_LOSS',*[c['id'] for c in expected]},'ALL_EXPANDED_TRIALS_REQUIRED')
    maps={r['id']:r for r in dynamic};save(directory/'dynamic_results.json',dynamic);save(directory/'tank_results.json',tanks)
    save(directory/'original17_traceability.json',prior['records']);save(directory/'original_five_failures.json',prior['failures']);save(directory/'standby_inventory_results.json',standby)
    metric=[dict(id=r['id'],status=r['status'],maximum_inlet_C=r['maximum_inlet_C'],maximum90_inlet_C=r['maximum90_inlet_C'],minimum_load_m3_h=r['minimum_load_m3_h'],cold_return_delay_s=r['cold_return_delay_s'],source_final_m3_h=r['source_final_m3_h'],maximum_primary_return_C=r['maximum_primary_return_C'],grades=json.dumps(r['grades'],sort_keys=True),parameters=json.dumps(r['parameters'],sort_keys=True)) for r in dynamic]
    csvout(directory/'failure_and_candidate_results.csv',metric)
    csvout(directory/'original17_traceability.csv',[dict(id=r['id'],status=r['status'],maximum_inlet_C=r['maximum_inlet_C'],minimum_load_m3_h=r['minimum_load_m3_h'],cold_return_delay_s=r['cold_return_delay_s'],parameters=json.dumps(r['parameters']),raw_sha256=json.dumps(r['raw_sha256'])) for r in prior['records']])
    grid={}
    for r in tanks:grid.setdefault((r['tank'],json.dumps(r['parameters'],sort_keys=True)),{})[r['layers'],r['dt_s']]=r
    conv=[]
    for (tank,key),v in grid.items():
        need(set(v)=={(20,.1),(40,.1),(80,.1),(160,.1),(160,.05)},'TANK_GRID_COVERAGE')
        rises=[v[n,.1]['outlet_rise_K'] for n in (20,40,80,160)];errors=[abs(a-b) for a,b in zip(rises,rises[1:])]+[abs(v[160,.1]['outlet_rise_K']-v[160,.05]['outlet_rise_K'])]
        conv.append(dict(tank=tank,parameters=json.loads(key),rise20_K=rises[0],rise40_K=rises[1],rise80_K=rises[2],rise160_K=rises[3],dt_error_K=errors[-1],all_grids_pass=all(r['outlet_rise_K']<=.5 for r in v.values()),fine80_160_and_dt_agree=max(errors[-2:])<=.05,numerical_status='NUMERICALLY_CONVERGED' if max(errors)<=.05 else 'NUMERICALLY_INCOMPLETE'))
    save(directory/'tank_convergence.json',conv);csvout(directory/'tank_convergence.csv',[dict(r,parameters=json.dumps(r['parameters'])) for r in conv])
    robust=[]
    for candidate in ('B','D','E'):
        rr=[r for r in dynamic if r['id'].startswith('robust_'+candidate+'__')];need(len(rr)==17,'EXACT_NEW17_CASES')
        fail=[r['id'] for r in rr if r['status']!='CONDITIONALLY_FEASIBLE']
        robust.append(dict(candidate=candidate,tested=17,failed_ids=fail,status='ROBUST_WITHIN_TESTED_ENVELOPE' if not fail else 'NOT_VERIFIED',scope='Only these17 finite injected conditions; no continuous probabilities or OEM qualification'))
    decision=[]
    for old in prior['failures']:
        c=old['parameters'];name='joint' if c.get('mixing_m3_s') else 'second' if c.get('second_source_failure') else 'measurement' if c.get('sensor_delay_s',.1)>1 else 'pump' if c.get('source_head_factor',1)<1 else 'capacity'
        volume=int(c.get('tank_volume_m3',15));new=maps['cause_'+name+'__physical_modified'+str(volume)];counter=maps['cause_'+name+'__single_counterfactual'+str(volume)]
        decision.append(dict(original_id=old['id'],original_peak_C=old['maximum_inlet_C'],original_min_load_m3_h=old['minimum_load_m3_h'],original_cold_return_delay_s=old['cold_return_delay_s'],root_categories=old['classifications'],first_violations={k:v for k,v in old.items() if k.startswith('first_')},counterfactual_id=counter['id'],counterfactual_status=counter['status'],new_case_id=new['id'],modified_parameters=new['parameters'],new_peak_C=new['maximum_inlet_C'],new_min_load_m3_h=new['minimum_load_m3_h'],new_cold_return_delay_s=new['cold_return_delay_s'],new_grades=new['grades'],original_raw_sha256=old['raw_sha256'],OEM='OEM_NOT_VERIFIED',procurement_blocked=True))
    save(directory/'failure_closure_decisions.json',decision);csvout(directory/'failure_closure_decisions.csv',[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in decision])
    fats=fat_rows();csvout(directory/'supplier_RFI_FAT.csv',fats);save(directory/'supplier_RFI_FAT.json',fats)
    protocols=['# 厂家COMPONENT_FAT / 集成FAT / 现场SAT拟议技术规范','','本文件为REQUIRED_VENDOR_CONFIRMATION，所有厂家试验NOT_RUN、保证/签章空缺，不代表已获客户批准。',
      '系统级90s连续性由集成方与业主负责，不强加给单台设备厂。测量不确定度扣除/加入后仍须满足原硬限，不放宽330/45/90/0.5。动态>=10Hz、稳态30min/末10min漂移<=0.1K均为拟议试验协议，不冒充本次仿真采样或正式标准。']
    for r in fats:
        protocols+=['','## '+r['id']+' '+r['equipment'],*['- '+k+': '+str(r[k]) for k in ('design_requirements','model_target_and_limits','measurement_method','COMPONENT_FAT','INTEGRATED_FAT','SITE_SAT','pass_criteria','rejection','required_raw_data')],'- 厂家签章：________；业主/集成方确认：________；日期：________；状态REQUIRED_VENDOR_CONFIRMATION。']
    (directory/'VENDOR_COMPONENT_FAT_INTEGRATED_FAT_SITE_SAT_ZH.md').write_text('\n'.join(protocols),encoding='utf-8')
    topologies=[dict(id='A',status='SIMULATED_PROPOSED_MODIFICATION',case='topologies__A',equipment='每条备用支路独立90m3/h泵/20kPa；隔离阀/止回阀/近远端TT/FT；自身湿源低负荷热服务；独立电源需OEM证明',limits='主源供液与小循环互斥；模型采用理想隔离，不证明实际预冷隔离阀动态/共因电源'),
      dict(id='B',status='NOT_RUN',case=None,equipment='专用旁通路径、双隔离阀/止回/流量/TT和独立电源',limits='00/01未证明该路由与A/B隔离；不能凭空增加现场旁通或假定不争抢330流量'),
      dict(id='C',status='SIMULATED_PROPOSED_MODIFICATION',case='topologies__C',equipment='独立90m3/h泵/20kPa、100kW换热或冷服务、隔离阀/止回/TT/FT、电源；RC另500/1000kW服务和330泵',limits='冷服务边界/冷端温度/OEM COP与电耗未知；不是免费冷量，也不是现有W2重复使用')]
    save(directory/'precooling_topologies.json',topologies)
    modifications=[]
    for name in ('A','B','C','D','E'):
        r=maps['option_'+name+'__nominal'];p=r['parameters'];modifications.append(dict(option=name,case=r['id'],result=r['grades'],equipment_changes=p,
            CAPEX_items='泵/阀/管路/HX/测点/电源/独立冷源按配置逐项报价，价格UNKNOWN',OPEX_items='实际附加泵热/用电在原始轨迹；塔风机/喷淋/COP/年气象map缺失，不报虚假节能率',OEM=None,procurement='BLOCKED'))
    save(directory/'modification_risk_cost_matrix.json',modifications)
    # Actual final charged tank states, not a hand-assigned85pct ideal profile.
    from .group_model.tank import Tank
    postcharge=[]
    for r in dynamic:
        if not r['id'].startswith('recharge_new__'):continue
        for name,state in r['final_tanks_k'].items():
            t=Tank(len(state),volume=r['parameters'].get('tank_volume_m3',15));t.t=list(state);first=t.t[0];mx=first;initial=t.energy();external=0
            for _ in range(900):
                old=t.t[0];t.advance(.1,330/3600,0,321.44,313.65,.005,.05);external+=.1*4036000*330/3600*(321.44-old);mx=max(mx,t.t[0])
            need(abs(t.energy()-initial-external)<1e-8*(initial+t.energy()+abs(external)),'POSTCHARGE_DISCHARGE_ENERGY')
            postcharge.append(dict(case=r['id'],tank=name,input_state_sha256=hashlib.sha256(json.dumps(state,separators=(',',':')).encode()).hexdigest(),outlet_rise_K=mx-first,status='CONDITIONALLY_FEASIBLE' if mx-first<=.5 else 'NO_FEASIBLE_DESIGN',scope='Actual final80-layer state only;not a replacement for cross-grid full dynamic recharge'))
    save(directory/'actual_postcharge_discharge.json',postcharge)
    report=['# 孟菲斯工程失败闭环决策表','', 'MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_NOT_VERIFIED；采购未放行。', '',
       f"计算source `{os.environ['GITHUB_SHA']}`，manifest `{sha(HERE/'source_manifest.json')}`。新动态{len(dynamic)}次、独立罐{len(tanks)}次。原始34案例/两组各17及各5失败均从官方ZIP逐文件SHA读取，不凭摘要猜ID。",'',
       '|原失败|原峰温°C/最小流量m³/h|原因|新对照ID|新峰温°C/流量|分项结果|OEM/采购|','|---|---|---|---|---|---|---|']
    for r in decision:report.append(f"|{r['original_id']}|{r['original_peak_C']:.6f}/{r['original_min_load_m3_h']:.6f}|{','.join(r['root_categories'])}|{r['new_case_id']}|{r['new_peak_C']:.6f}/{r['new_min_load_m3_h']:.6f}|{json.dumps(r['new_grades'],ensure_ascii=False)}|缺保证/阻塞|")
    report+=['','## 原5失败与因果链','',
       '五项身份逐一见original_five_failures.json：冷源能力×0.8；源H0×0.97；观测延迟1.2s；接管中W2在60s再失效；联合不利角点。能力/曲线/观测变更从t0即存在，W1在30s失效，不可把所有变化都说成30s注入。每项有同输入单变量反事实及新物理方案；取消二次故障只是必要性反事实，不是硬件修复。',
       '容量不足→罐耗冷→温度/取备用动作→可能负荷侧停流；源曲线不足→实际交点不足330→冷返资格失败；过期观测→冻结M1/独立保护正确拒绝→不能获得连续供冷资格；二次失效→无可用源→库存继续消耗；联合角点保留全部同时输入，不拼接单轴极值。具体第一违规时间、排热、泵/阀和库存曲线均在原始追溯矩阵。',
       '', '## 联合候选及残余失败','',json.dumps(robust,ensure_ascii=False,indent=2),
       '不是所有双故障都已被业主列入设计基准；本轮把单故障、维修/维护、接管中再故障、源总管/负荷总管共因风险分别保存。不得自动套TierIII或作认证。若没有所有要求均通过的候选，结论NO_FEASIBLE_CANDIDATE，不把安全拒绝当冷却PASS。',
       '', '## 16项答复与决策边界','',
       '1/2. 两组原17中的5失败、精确ID/参数/hash及直接原因见首表与JSON，包含初始条件、故障窗口及后续次生事件。',
       '3. 项目控制可改进实际Ready准入、测量过期拒绝、设计流量不足的备用源接管及零速/闭阀顺序；冻结M1完全不改。1.2s链路不能靠放宽1s有效期修好；更快独立测量链是新增硬件假设，原慢链不用作有效数据。',
       '4. 能力/泵交点不足、预冷缺失、双源失效及负荷共管失效需相应物理改动。备用泵升速/整套源接管可能消除部分问题，但必须看实际联合输出，不能靠软件创造冷量或无缝切罐。',
       '5/6. 15m3罐是否继续使用取决于实际冷量/分层与本次全部网格。85pct真实初始量≠17TT能保守证明85pct，更不等于旧4TT可证明；本轮90pct候选以17TT、0.2K拟议不确定度做保守估计，单调温层及未测区域须FAT实证。回充后的真实层状态再放冷已单列，不能手工重置成理想85pct。',
       '7/8. 已模拟A独立小循环与C独立冷服务/HX，泵/阀/测点/电源全部列为新增；B专用旁通因路由/隔离缺资料NOT_RUN。不能推荐凭空已有的旁通。A设备少但依赖同一湿源；C隔离较强但增成本/冷服务/COP和电源依赖，最终需施工图及OEM证明。',
       '9. 模块退出按真实并联支路减少而非只减平均kW；4模块各82.5m3/h、每模块>=约679.038kW只是必要下界。MODULE_FAILURE结果同时展示容量、压降、剩余四模块与切备用整套，需风机/喷淋/盘管map证明。',
       '10. PUMP_FAILURE比较3pct退化的速度补偿、V9/R10上限、单泵退出及备用泵；真实流量和泵热独立复算。额定电机kW不能替代Q-H；静压/NPSHr/弱件MAWP与水锤未知，R10<=18m不能靠提高H0绕过。',
       '11. 第三源W3在模型中是新增独立源及其独立接口；源总管故障只在W3独立源侧接口假设下可隔离。共用负荷总管故障仍可能不能由源冗余解决，需要真正独立负荷供液通道/电源/控制域与业主可靠性基准；不掩盖。',
       '12. VALVE_FAILURE明确A隔离需求/PLC请求B、实际卡阀与物理流量后果，独立断言没有需求就报测试失败；假开反馈用实际流量复核。即使不卡阀，当前单负荷选择器break-before-make也可能短时断330，不能用“安全切换”冒充无缝连续供冷。',
       '13/14. 最少修改和最低残余风险不是同一指标。保留A、只加预冷B、预冷+分层C、预冷+能力/泵D、加强隔离E逐一实算，最终三个候选见下；没有价格/map/概率，不声称经济全局最优或风险量化排名。',
       '15/16. 可立即发supplier_RFI_FAT.csv及中文分层FAT/SAT规范要求报价/保证；COMPONENT_FAT只约束本体，90s完整系统连续性归INTEGRATED_FAT/SITE_SAT。所有保证/签章空缺，厂家试验NOT_RUN；协议精度、采样和稳态条件待双方确认，不冒充正式标准。',
       '', '## 最终OPTION A / B / C','',
       '- OPTION A：尽量保持00/01数量及15m3，最低必要能力补强；无真实预冷/库存/流量证据时不能通过。对应option_A及D补强对照，不自动更改客户方案。',
       '- OPTION B：90m3/h独立预冷+拟议100kW热能力、90pct初充、17TT/快测链、合成能力×1.15/速度裕量3pct/备用泵；对应D全17。仍须OEM共同工况、压力与故障隔离证明。',
       '- OPTION C：对应E，增加W3独立源/源侧接口/预冷和20m3罐；独立RC回充另列500/1000kW+330泵试验。负荷总管与执行器共因风险不能因第三源自动消失。',
       '', '## 完成状态','',
       'SOFTWARE_EXECUTION_STATUS=COMPLETED_SOURCE_BOUND_DEVELOPMENT；PHYSICAL_MODEL_VALIDITY=EQUATIONS_VERIFIED_WITH_UNCALIBRATED_ASSUMPTIONS；FAILURE_CLOSURE_STATUS=PER_CASE_PARTIAL；ROBUSTNESS_STATUS=见17项分表；VENDOR_EVIDENCE_STATUS=OEM_NOT_VERIFIED；CUSTOMER_DESIGN_APPROVAL_STATUS=NOT_APPROVED；PROCUREMENT_RELEASE_STATUS=BLOCKED。',
       '保留原C3-C、M1和全部历史证据。没有正式资格、硬件控制、生产、采购或Phase6授权。真实成本/年度性能/概率缺失时只列CAPEX/OPEX变化项，不编采购价和节能率。']
    text='\n'.join(report)+'\n';(directory/'MEMPHIS_FAILURE_CLOSURE_ZH.md').write_text(text,encoding='utf-8')
    save(directory/'robustness_results.json',robust)
    payload=dict(source_commit=os.environ['GITHUB_SHA'],manifest_sha256=sha(HERE/'source_manifest.json'),dynamic_trials=len(dynamic),tank_trials=len(tanks),original_cases=34,original_failures=10,robustness=robust,groups=groups,final_candidates='NO_FEASIBLE_CANDIDATE' if all(r['failed_ids'] for r in robust) else 'CONDITIONALLY_FEASIBLE_WITHIN_REGISTERED17_ONLY_NOT_OEM_APPROVED',engineering='MEMPHIS_ENGINEERING_NOT_APPROVED',vendor='OEM_NOT_VERIFIED',formal=False,procurement=False,hardware=False,phase6=False)
    save(directory/'closure_summary.json',payload)
    plots=''.join(plot([dict(id=r['id'],peak=r['maximum_inlet_C'],flow=r['minimum_load_m3_h'],status=r['status']) for r in dynamic],'flow','peak','实际负荷最小流量—机柜峰温',45) for _ in range(1))
    for tank in ('A','B'):plots+=plot([dict(id=str(r['parameters']),volume=r['parameters']['volume'],rise=r['rise20_K'],status=r['numerical_status']) for r in conv if r['tank']==tank],'volume','rise',tank+'罐20层最不利对照／完整网格另见表',.5)
    data={r['id']:json.loads((locations[r['id']].parent/'plot_data.json').read_bytes()) for r in dynamic}
    # G_WET_LOSS plot lives at its stage root as do all bundle plots.
    doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>孟菲斯失败闭环与厂家验证</title><style>body{max-width:1180px;margin:auto;padding:24px;font:16px/1.65 system-ui;color:#193743;background:#f7fafb}pre{white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;max-height:320px;background:white}svg text{font:13px system-ui}select{max-width:100%;font:inherit;padding:8px}h1,h2{line-height:1.3}.warning{padding:18px;background:#fff0de;border-left:4px solid #b45c24}</style><h1>孟菲斯 · 失败闭环与厂家验证</h1><p class="warning">MEMPHIS_ENGINEERING_NOT_APPROVED / OEM保证空缺 / 采购阻塞。安全拒绝不等于连续供冷通过；新增回路是提案，不是00/01现有设备。</p>'+plots
    doc+='<h2>实际执行场景</h2><select id="case">'+''.join('<option>'+html.escape(r['id'])+'</option>' for r in dynamic)+'</select><pre id="verdict"></pre><div id="curves"></div><details><summary>完整中文决策表、16项回答及缺口</summary><pre>'+html.escape(text)+'</pre></details>'
    js=json.dumps(dict(series=data,results=maps),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    doc+='<script>const data='+js+''';const select=document.getElementById('case');function draw(){const r=data.results[select.value],rows=data.series[select.value];document.getElementById('verdict').textContent=JSON.stringify({grades:r.grades,status:r.status,peak_C:r.maximum_inlet_C,min_load_m3_h:r.minimum_load_m3_h,cold_delay_s:r.cold_return_delay_s,excitation:r.excitation,first_violations:r.first_violations_s,events:r.events},null,2);let out='';for(const [keys,label,lim] of [[['rack_C','primary_C'],'机柜入口/一次供液 °C',45],[['load_m3_h','source_m3_h','recharge_m3_h'],'负荷/源/回充 m³/h',330],[['cold_A_m3','cold_B_m3'],'A/B真实阈值冷库存 m³',null]]){let vals=rows.flatMap(p=>keys.map(k=>p[k]));if(lim!==null)vals.push(lim);let lo=Math.min(...vals),hi=Math.max(...vals),pad=Math.max(.2,(hi-lo)*.08);lo-=pad;hi+=pad;let xmax=rows[rows.length-1].time_s,s='<h3>'+label+'</h3><svg viewBox="0 0 800 250" role="img" aria-label="'+label+'">';for(let j=0;j<5;j++)s+='<text x="8" y="'+(30+40*j)+'">'+(hi-(hi-lo)*j/4).toFixed(2)+'</text><text x="'+(65+705*j/4)+'" y="225">'+(xmax*j/4).toFixed(0)+'s</text>';keys.forEach((k,i)=>s+='<polyline fill="none" stroke="'+['#167885','#bd6524','#667d8a'][i]+'" stroke-width="2" points="'+rows.map(p=>(65+705*p.time_s/xmax).toFixed(2)+','+(190-160*(p[k]-lo)/(hi-lo)).toFixed(2)).join(' ')+'"/>');if(lim!==null)s+='<path d="M65 '+(190-160*(lim-lo)/(hi-lo))+'H770" stroke="#b33" stroke-dasharray="4 3"/>';out+=s+'</svg><p>'+keys.join(' / ')+'</p>';}document.getElementById('curves').innerHTML=out;}select.addEventListener('change',draw);draw();</script></html>'''
    (directory/'engineering_report.html').write_text(doc,encoding='utf-8');return dict(kind='final',**payload,report_sha256=sha(directory/'MEMPHIS_FAILURE_CLOSURE_ZH.md'))
