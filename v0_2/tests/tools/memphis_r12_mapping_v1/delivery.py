"""One consolidated mapping package; SVG is a lossless graph atlas, not CAD."""
import csv
import io
import json
import hashlib
import html
import math
from pathlib import Path
from .topology import ref


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(value):
    if isinstance(value,float) and not math.isfinite(value):
        return {"invalid_numeric_input":str(value)}
    if isinstance(value,dict): return {k:safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [safe(v) for v in value]
    return value


def save(path,value):
    Path(path).write_text(json.dumps(safe(value),ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def csv_file(path, rows, fields):
    with Path(path).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def functional_svg(g, target):
    """Readable overview plus every directed branch in a graph atlas.

Every atlas row is one exact JSON edge with XML data attributes; no unregistered
fluid line is added. HX heat-coupling boxes are non-fluid relationships.
"""
    esc=lambda s:html.escape(str(s),quote=True)
    rows=len(g["edges"]); height=780+rows*30+110
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1680 {height}" role="img" aria-label="R12功能验证图及完整支路清单，非施工图">',
      '<defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#1e293b" stroke-width=".5"/></pattern><marker id="a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><path d="M0 0L10 3.5L0 7Z" fill="#64748b"/></marker></defs>',
      '<style>text{font-family:"Cascadia Code","Microsoft YaHei",sans-serif;fill:#e2e8f0}.title{font-size:24px;font-weight:700}.body{font-size:16px}.small{font-size:12px}.sub{fill:#94a3b8}</style>',
      f'<rect width="1680" height="{height}" fill="#0f172a"/><rect width="1680" height="{height}" fill="url(#grid)"/>',
      '<text x="35" y="46" class="title">R12 三层身份与流路验证图 · R12-MAPPING-v1</text>',
      '<text x="35" y="78" class="body" fill="#fbbf24">过程验证图，可版本化修改；原图保留。PARTIALLY_MAPPED_BLOCKED / 非施工批准</text>']
    def box(x,y,w,h,color,title,lines):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#0f172a"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{color}" fill-opacity=".12" stroke="{color}"/>')
        parts.append(f'<text x="{x+18}" y="{y+30}" class="body">{esc(title)}</text>')
        for i,line in enumerate(lines): parts.append(f'<text x="{x+18}" y="{y+57+23*i}" class="small sub">{esc(line)}</text>')
    box(35,110,480,145,"#22d3ee","一次网 A / BT-A / LP-A",["一次供回成对，禁止 A 取液、B 回液","共享源泵是分时切网，不是 A/B 连通桥","T-2 示例：LP-A 运行，LP-B 停止"])
    box(555,110,525,145,"#a78bfa","三对 CDU：C01A/B · C02A/B · C03A/B",["CDU 身份 ≠ 一次网身份","任一 CDU 的 P1 阀组独立选择 A 或 B","一次/二次之间只有 HX 热耦合，无流体边"])
    box(1120,110,525,145,"#34d399","二次 A/B 环与 18 柜四阀",["每 CDU 两台 100% 泵，一用一备","每柜 AS/AR/BS/BR，柜外选择","短时并流：≤2K / ≤5kPa 稳定5s / ≤30s"])
    for u in range(1,4):
        y=295+(u-1)*90
        box(35,y,1580,65,"#60a5fa",f"U{u}  六柜单元",[f"C{u:02d}A 或 C{u:02d}B → 二次环 A 或 B → R01 … R06；备用 CDU B 可使用一次网 A"])
    box(35,585,760,125,"#fb7185","仍需设计澄清 / 不能自动放行",["PID-005 贯通线没有建成真实旁通；滤器内部阀位未定","压力主站跟随策略、泵曲线/瞬态、M2 定值尚未闭合","此图只验证功能意图，不证明 90s 热水力连续性"])
    box(835,585,810,125,"#fbbf24","源泵回充：无独立 RC / 无 CP-1/2",["停泵证明 → 旧网隔离 → 目标网建路 → 启泵 → 实际流量","冷液返回 → 独立储冷证明；B 回充完成 ≠ 双罐恢复","440 m³/h / 约3.62 MW 只是算例，不是单湿塔运行保证"])
    parts.append('<text x="35" y="750" class="body">完整节点—支路图谱（每行对应 JSON 中一条边，方向及阀/泵依赖必须同时满足）</text>')
    for i,e in enumerate(g["edges"]):
        y=780+i*30
        color="#22d3ee" if e["fluid_domain"]=="PG25_PRIMARY" else "#34d399"
        attrs=' '.join(f'data-{k}="{esc(e[v])}"' for k,v in (("edge-id","id"),("upstream","upstream"),("downstream","downstream"),("domain","fluid_domain")))
        parts.append(f'<g {attrs}><path d="M38 {y}H75" stroke="{color}" stroke-width="2" marker-end="url(#a)"/>')
        parts.append(f'<text x="88" y="{y+4}" class="small">{esc(e["id"])}: {esc(e["upstream"])} → {esc(e["downstream"])}</text>')
        deps="V="+",".join(e["valve_dependencies"])+" P="+",".join(e["pump_dependencies"])
        parts.append(f'<text x="990" y="{y+4}" class="small sub">{esc(deps)}</text></g>')
    y=height-65
    parts.append(f'<text x="35" y="{y}" class="small sub">青色：一次流体边；绿色：二次流体边。上方卡片为分组说明，不增加物理管路。HX 热耦合不属于流体连边。</text>')
    parts.append(f'<text x="35" y="{y+26}" class="small sub">共 {len(g["edges"])} 支路 / {len(g["ports"])} 端口。资料：S2 阀位矩阵；S3 PID-002/004/005/006/008/009。MEMPHIS_ENGINEERING_NOT_APPROVED</text></svg>')
    Path(target).write_text("\n".join(parts),encoding="utf-8")


def write_package(g, results, directory, source_manifest, environment):
    out=Path(directory);out.mkdir(exist_ok=True)
    save(out/"R12_EXECUTABLE_TOPOLOGY.json",g)
    csv_file(out/"R12_COMPONENT_PORT_REGISTRY.csv",[
        dict(record_type="COMPONENT",id=c["tag"],**c) for c in g["components"]]+[
        dict(record_type="PORT",**p) for p in g["ports"]],
        ["record_type","id","equipment_tag","tag","kind","fluid_domain","primary_network","primary_network_candidates","secondary_network","secondary_network_candidates","direction","confirmation","use","source_refs"])
    identity=[dict(unit=c["unit"],CDU_IDENTITY=c["CDU_IDENTITY"],secondary_network=c["secondary_network"],
             allowed_primary_networks="A or B (paired selector)",tank_from_CDU_identity=False,source_refs=c["source_refs"])
              for c in g["components"] if c["kind"]=="CDU"]
    csv_file(out/"R12_CDU_IDENTITY_MAPPING.csv",identity,["unit","CDU_IDENTITY","secondary_network","allowed_primary_networks","tank_from_CDU_identity","source_refs"])
    sequences=[
       ("T2",1,"OPEN_NEW_PRIMARY","new CDU P1 current-network pair open; opposite pair closed","actual pair feedback + primary FT","PID-005; 阀位矩阵 A8:O8"),
       ("T2",2,"MATCH_SECONDARY","retain old path; new master not granted","two-channel deltaT<=2K/dp<=5kPa continuously5s","PID-006"),
       ("T2",3,"CONTROLLED_OVERLAP","new rack S/R pair open; old master retained initially","actual local/rack flow; overlap<=30s","PID-006; follower control OPEN"),
       ("T2",4,"REVOKE_AND_STOP","request old master revoke and old pump stop","actual revoke + zero speed, not closed-valve inference","PID-005/006"),
       ("T2",5,"ISOLATE_OLD","close old rack pair/P2/P1 after zero proof","all actual old path closed; master NONE","PID-006; T2 candidate mapping"),
       ("T2",6,"GRANT_NEW_MASTER","request one new master only","actual new sole master + paths + released local/rack FT","PID-006; candidate completion gate"),
       ("T1",1,"SAME_PRIMARY_SOURCE_CHANGE","prepare new source on same primary; CDU identity unchanged","new source flow+cold return; isolate old source","PID-009 T1; no dynamic startup implementation"),
       ("RECHARGE",1,"STOP_SOURCE_PUMPS","LP running network unchanged; stop shared SP01..04","all actual zero-speed proofs + running tank budget permission","PID-008 step1/2"),
       ("RECHARGE",2,"CLOSE_OLD_NETWORK","close old SRC-H/S and source-unit S/R","all closed feedback, source pumps still stopped","PID-008 step3"),
       ("RECHARGE",3,"OPEN_TARGET_NETWORK","open only target paired headers and source branch","actual valves+suction/liquid permission","PID-008 step4"),
       ("RECHARGE",4,"RESTART_AND_PROVE","restart shared source pumps","actual FT + valid target path + cold return","PID-008"),
       ("RECHARGE",5,"RESERVE_PROOF","no automatic dual-ready","independent reserve evidence; performance/time budget OPEN","PID-008")]
    seq=[dict(mode=m,step=i,state=s,command=c,required_proof=p,source_locator=r) for m,i,s,c,p,r in sequences]
    csv_file(out/"R12_VALVE_SEQUENCE_MATRIX.csv",seq,["mode","step","state","command","required_proof","source_locator"])
    save(out/"R12_PRIMARY_SECONDARY_NETWORK_MAP.json",dict(
        CDU_IDENTITY=[x["CDU_IDENTITY"] for x in identity],PRIMARY_NETWORK_ID=["A","B"],
        SECONDARY_NETWORK_ID=["A","B"],identity_mappings=identity,
        heat_only_interfaces=g["heat_couplings"],primary_cross_connect_allowed=False,
        fluid_domain_note="secondary A/B may transiently connect only at released permitted rack paths; never via HX to primary"))
    save(out/"R12_CONTROL_PERMISSIVES.json",dict(version="R12-INTENT-CONTROL-v1",use="UNIT_TEST_ONLY",source_refs=[ref("S3","PDF p7 PID-006")],
        registered={"delta_T_max_K":2,"delta_p_max_kPa":5,"stable_duration_s":5,"overlap_max_s":30,"pressure_masters_max":1},
        gates=["TEMP_MATCH_VALID","PRESSURE_MATCH_VALID","STABLE_5S_VALID","PRESSURE_MASTER_TRANSFER_VALID","OVERLAP_TIMER_VALID","SENSOR_FRESHNESS_VALID","VALVE_FEEDBACK_VALID","FLOW_ESTABLISHED_VALID"],
        engineering_unknowns=g["open_runtime_values"],unit_fixture_policy={"freshness_s":.5,"max_sample_gap_s":.5,"cold_return_limit_C":40.,"status":"SYNTHETIC_TEST_ONLY_NOT_APPROVED_CONTROL_DEFAULT"},
        actuator_issue_receipts="NONE_THIS_IS_NOT_PLC_EXECUTION",PRE_Safety_PLC_POST="FROZEN_M1_NOT_IMPORTED_OR_MODIFIED; DYNAMIC_INTEGRATION_PENDING"))
    save(out/"R12_STATIC_CONNECTIVITY_TESTS.json",dict(scope="STATIC_AND_UNIT_ONLY",tests=[r for r in results if not r["negative"]]))
    save(out/"R12_NEGATIVE_CONTROL_RESULTS.json",dict(scope="SYNTHETIC_UNIT_REFUSAL_NOT_HARDWARE",tests=[r for r in results if r["negative"]]))
    differences=[
      dict(legacy="CDU_B primary = B tank",R12="Any CDU independently selects primary A or B",status="LEGACY_ASSUMPTION_NOT_REUSED",source="PID-005/009 T2"),
      dict(legacy="CDU transfer implies B tank depletion",R12="T2 primary A/LP-A; B tank standby",status="LEGACY_ASSUMPTION_NOT_REUSED",source="阀位矩阵 A8:O8"),
      dict(legacy="one equivalent CDU secondary pump",R12="two distinct 100% pumps per CDU",status="INTENT_GRAPH_REPLACED_NOT_HYDRAULIC_CALIBRATED",source="PID-005"),
      dict(legacy="aggregate rack resistance/flow",R12="18 independent four-valve rack branches",status="INTENT_GRAPH_REPLACED_LOCAL_FLOW_REQUIRED",source="PID-006"),
      dict(legacy="independent RC/CP1/2 assumed",R12="common source pump sequential recharge",status="NOT_ORIGINAL_R12_EQUIPMENT",source="PID-008"),
      dict(legacy="old takeover no explicit matching/master proofs",R12="5s temp/pressure + <=30s overlap + actual revoke/isolate/grant",status="NEW_UNIT_MAPPING_NO_INHERITED_PASS",source="PID-006"),
      dict(legacy="sealed historical development/formal outcomes",R12="remain attributed to registered original source; no relabel",status="PRESERVED_UNCHANGED",source="project AGENTS; no frozen imports")]
    csv_file(out/"R12_LEGACY_MODEL_DIFFERENCES.csv",differences,["legacy","R12","status","source"])
    issues=[]
    for x in g["source_issues"]:
        y=dict(x)
        y["this_round"]="OPEN_ENGINEERING"
        if x["id"] in ("R12-I01","R12-I02","R12-I04","R12-I05"):
            y["this_round"]="FUNCTIONAL_INTENT_MAPPED_AND_UNIT_SCOPE_TESTED; DYNAMIC_OR_OEM_NOT_CLOSED"
        issues.append(y)
    issues += [dict(id="MAP-I14",priority="P0",topic="压力跟随与内部循环细节",status="OPEN",this_round="FOLLOWER_CONTROL_AND_INTERNAL_FILTER_VALVE_TAGS_NOT_DESIGNED",detail="图中未完整给出新泵并流期间调速/防死压策略、过滤器隔离阀位；本轮仅功能许可测试，禁止动态或硬件放行",refs=[ref("S3","PDF p6 PID-005; p7 PID-006")]),
      dict(id="MAP-I15",priority="P0",topic="每CDU一次流量证明与压差双链",status="OPEN",this_round="MEASUREMENT_ADDITION_PROPOSED_NOT_DRAWN_OR_OEM_VERIFIED",detail="组FT不能代替单CDU一次FT。新增P1-FT接口是单元测量契约建议，不冒充原图已画仪表。并流压差来源/冗余释放链亦待设计。",refs=[ref("S3","PDF p6 PID-005; p7 PID-006; p10 PID-009")])]
    csv_file(out/"R12_OPEN_ENGINEERING_ISSUES.csv",issues,["id","priority","topic","status","this_round","detail","refs"])
    states="""# R12 T-1 / T-2 与共用源泵状态机

本文件是过程验证版本，不是不可修改的施工图。原 R12 文件哈希保留，新图由节点—支路 JSON 同源生成。

## 三层身份

CDU_IDENTITY、PRIMARY_NETWORK_ID、SECONDARY_NETWORK_ID 是不同 Enum。一个单元二次环 A/B 对应 CnnA/CnnB，但不能由这个字母推出一次网和罐。T-2 当前一次 A 时，备用 CnnB 打开自己的 P1-AS/AR，P1-BS/BR 关闭。LP-A 不变，LP-B 无启动请求。

## T-2

OPEN_NEW_PRIMARY → WAIT_SECONDARY_MATCH → OVERLAP_WAIT_FLOW → WAIT_OLD_STOP_AND_REVOKE → WAIT_OLD_ISOLATION → WAIT_NEW_MASTER → COMPLETED_UNIT_INTENT_ONLY。

每次只读取已释放、未过期双通道测试观测。不访问 plant、future command 或 M1。匹配持续时间由逐条有序观测累积，不接受一个外来 stable=true。旧主撤销及停泵零速证明后才请求旧路隔离；旧路实际关到位后才请求授予新主；至少后续一个观测才能证实授予。流量需要新 CDU 一次、二次和六柜各自测量，且图上具备真实启用流路。状态名不代替测量。

缺测、未来释放、非法一次串网、双主、卡阀均不宣布完成，保留现有可用路径并请求独立负载保护。超30s进入 HOLD；本单元软件无法保证未知泵/阀动态下仍有连续供流，不能将 HOLD 当成物理成功。压力跟随调速方式、滤器内部阀组、测量允差/新鲜度的工程定值仍 OPEN。测试用0.5s不是图纸批准值。

## T-1

仅同一次网源切换的终态门禁：新源实际流路/流量/冷返、旧源隔离，CDU身份及一次网不变。不实现冷塔60s建冷等动态，不声称全事件过程验证。图纸允许的同网源短暂重叠与一次A/B并通严格区分。

## 共用源泵分段补冷

WAIT_STOP_PROOF → WAIT_OLD_CLOSED → WAIT_TARGET_PATH → WAIT_ACTUAL_FLOW → WAIT_COLD_RETURN → WAIT_RESERVE_PROOF → TARGET_RESERVE_PROVEN_UNIT_FIXTURE_ONLY。

运行罐的预算许可必须外部独立给出，未提供不能自动开始。全部源泵零速不能用关阀推断。B回充结束只产生 B_RECHARGE_DONE；不自动产生 A_RESERVE_READY、DUAL_RESERVE_READY、SECOND_FAULT_QUALIFIED。R-2回A时同序反向，净冷量与泵/塔能力留待动态验证。440m3/h及3.62MW不作为实测性能或默认设点。

## 不确定管线

PID-005 疑似中间贯通线没有作为实际旁通加入。当前图表达“泵→过滤→板换”的文字意图；过滤器 SERVICE 仅为模型支路可用性，不是已批准的实际阀位。设计方可在新验证图中确认/修订；确认前动态 admission 为 PARTIALLY_MAPPED_BLOCKED。
"""
    (out/"R12_T1_T2_STATE_MACHINE.md").write_text(states,encoding="utf-8")
    functional_svg(g,out/"R12_FUNCTIONAL_PID.svg")
    # XML attributes are independent of the human-readable edge labels.
    import xml.etree.ElementTree as ET
    root=ET.parse(out/"R12_FUNCTIONAL_PID.svg").getroot()
    drawn={e.attrib["data-edge-id"]:(e.attrib["data-upstream"],e.attrib["data-downstream"],e.attrib["data-domain"]) for e in root.iter() if "data-edge-id" in e.attrib}
    expected={e["id"]:(e["upstream"],e["downstream"],e["fluid_domain"]) for e in g["edges"]}
    assert drawn==expected,"SVG_JSON_GRAPH_MISMATCH"
    passed=sum(x["status"]=="PASS" for x in results)
    status={"SOURCE_REGISTERED":"PASS_ORIGINAL_BYTES_RECHECKED_LOCALLY; HASH_BOUND_INTAKE_USED_REMOTELY",
        "TOPOLOGY_MAPPED":"DECLARED_FUNCTIONAL_INTENT_PARTIAL; PID005_CONNECTIVITY_BLOCKED",
        "CONTROL_IMPLEMENTED":"T2_UNIT_STATE_MACHINE; T1_TERMINAL_GATE; RECHARGE_UNIT_SEQUENCE",
        "UNIT_TESTED":f"{passed}/{len(results)}"+ (" PASS" if passed==len(results) else " FAIL"),
        "DYNAMICALLY_VALIDATED":"NO", "OEM_VERIFIED":"NO", "ENGINEERING_APPROVED":"NO"}
    report=f"""# R12 拓扑与阀序映射 V1

结论：{passed}/{len(results)} 项静态/合成单元验证通过。不是动态热水力 PASS。总 admission 保持 **PARTIALLY_MAPPED_BLOCKED**，工程状态保持 **MEMPHIS_ENGINEERING_NOT_APPROVED**。

## 十项回答

1. 三个 A/B 维度已用独立类型拆开，错误类型互换被拒绝。
2. T-2 中 CDU B 可通过自身 P1-AS/AR 接一次网 A。不是改标签：新 CDU 一次/二次、柜外供回实际反馈图路和流量门禁均检查。
3. T-2 的 B 罐负载路径关闭，LP-B 无启动请求。证明范围为零启用负载支路，不是完成了罐温度/耗冷积分仿真。
4. 18柜72选择阀、6台CDU12台二次泵逐件展开。G01 是单组模板实例，未冒充现场竣工位号。
5. ≤2K、≤5kPa持续5s、≤30s重叠、单压力主站撤销/隔离/授予已实现单元门禁。泵跟随模式与测量工程定值仍待定义，不能据测试宣布实际控制能力验证完成。
6. 一次 A/B 非法并通、A供B回、源侧共用泵串网均被拒绝。二次受控重叠不授予一次并通权限。
7. 共用源泵按停泵→旧网关闭→目标建路→重启→流量→冷返→独立储冷证明建图并作合成序列验证；没有 RC/CP1/2。R-2净恢复、A/B双罐再次90s和第二次故障未验证。
8. 废弃固定 CDU-B→一次B罐、接管自动耗B、总管流量替代每柜/单元流量、单等效二次泵与默认独立RC等旧假设。旧程序/证据未覆盖、不改名借PASS。
9. PID-005贯通线、压力主站跟随实现、滤器内部阀组、每CDU一次FT/并流压差测量链、泵扬程/曲线、OEM UA、M2定值、气象分钟CSV、正式设计签署仍未闭合。P1-FT是拟增测量接口，不冒充原图已有仪表。R12为可修订的过程图，原件留存，新图标出修订/待定，不要求把草稿当作不可修改。
10. 已具备已声明意图的有界静态/单元执行条件，尚不具备“R12全图已确认”的动态工程放行。下一轮先解决上述P0接口，再单独登记动态模型与预算。

## 状态分开

"""+"\n".join(f"- {k}: {v}" for k,v in status.items())+f"""

## 验证证据与边界

正向和负向结果分别见 JSON，含逐观测命令、实际阀/泵反馈、FT、许可、预期/实得、资料依据；均明确 SYNTHETIC_UNIT，不生成 PLC issue 收据。
源参数采用哈希绑定接收层，S5仅结构参考。静态注册数：{len(g['components'])}组件记录、{len(g['ports'])}端口、{len(g['edges'])}有向支路、{len(g['sensors'])}测点。组件含模型过滤器可用性抽象，不是物理采购数量。
基础热接口：18×147.25=2650.5kW，每六柜883.5kW，经所选CDU映射；测试不是UA求解，不含泵热/罐储热，不证明实际冷源容量或完整能量守恒。没有流路时热负载不能消失，应保留未移除热量。
SVG完整支路图谱与JSON逐边核对一致：{len(drawn)}条。不是施工CAD；尺寸、管径选择、阀Cv/动作、NPSH、水锤、定压/泄压须专业深化。
本轮CPU25%、单Python进程256MiB/Job512MiB、480s上限；没有本机Python/模型运行，没有1800s仿真，没有采用60/105分钟预算，没有正式C3-C/生产/硬件/采购/Phase6授权。

## 下一轮候选（未启动、预算未批准）

先定义压力跟随与滤器内部可施工阀序；再分开注册单单元T2、同网T1、A运行分段补B/返回补A及真实末态第二次故障。物理时长先围绕切换窗口逐例登记；1800s恢复仍需独立预算。执行耗时无R12动态基准，当前不虚报分钟估计。保持CPU25%和已批准内存上限，若动态模型需提高则另请批准。

## 来源与执行

执行commit：{environment['source_commit']}。Python：{environment['python']}。镜像：{environment['image']}。
源码、输入、共享监督器与工作流原始SHA256：R12_SOURCE_INPUT_ENVIRONMENT_MANIFEST.json。全部交付字节：R12_DELIVERY_HASHES.json。
"""
    (out/"R12_MODEL_MAPPING_REPORT_ZH.md").write_text(report,encoding="utf-8")
    save(out/"R12_STATUS.json",status)
    template=(Path(__file__).parent/"report_template.html").read_text(encoding="utf-8")
    data=json.dumps(dict(cases=[x for x in results if x["id"].startswith(("CASE01_","CASE02_","CASE03_"))],statuses=status,report=report),ensure_ascii=False,allow_nan=False).replace("<","\\u003c")
    viewer=template.replace("__ATLAS__",(out/"R12_FUNCTIONAL_PID.svg").read_text(encoding="utf-8")).replace("__EVIDENCE__",data)
    (out/"engineering_report.html").write_text(viewer,encoding="utf-8")
    save(out/"R12_SOURCE_INPUT_ENVIRONMENT_MANIFEST.json",dict(source_manifest=source_manifest,environment=environment,
        graph_revision=g["revision"],control_revision="R12-INTENT-CONTROL-v1",svg_json_check={"status":"PASS","edges":len(drawn)},
        authorities=dict(development=True,git_dedicated_branch=True,remote_unit_tests=True,long_simulation=False,formal_C3C=False,hardware=False,production=False,phase6=False)))
    save(out/"R12_DELIVERY_HASHES.json",dict(records=[dict(path=f.name,bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(out.iterdir()) if f.is_file()]))
    return dict(tests=len(results),passed=passed,failed=len(results)-passed,statuses=status,svg_json_edges=len(drawn))
