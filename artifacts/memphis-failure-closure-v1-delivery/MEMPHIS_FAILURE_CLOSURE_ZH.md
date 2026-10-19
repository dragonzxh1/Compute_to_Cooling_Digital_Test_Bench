# 孟菲斯工程失败闭环决策表

MEMPHIS_ENGINEERING_NOT_APPROVED；OEM_NOT_VERIFIED；采购未放行。

计算source `be3e9ea395ebd461683190d6cf3a0d5125973e13`，manifest `ba263422c76d02710e410c2071cc87b84d6faee82fd0d65e94cc4148adee7ce2`。新动态127次、独立罐340次。原始34案例/两组各17及各5失败均从官方ZIP逐文件SHA读取，不凭摘要猜ID。

|原失败|原峰温°C/最小流量m³/h|原因|新对照ID|新峰温°C/流量|分项结果|OEM/采购|
|---|---|---|---|---|---|---|
|ROBUST_B15_02|44.956796/0.000000|A_HEAT_REJECTION_SHORTFALL|cause_capacity__physical_modified15|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_B15_06|44.000054/330.000000|D_PUMP_NETWORK_SHORTFALL|cause_pump__physical_modified15|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_B15_11|44.000054/330.000000|H_OBSERVATION_STALE_F_RESTRICTION|cause_measurement__physical_modified15|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_B15_12|50.038797/330.000000|G_REDUNDANCY_LOSS_OWNER_DESIGN_BASIS_PENDING|cause_second__physical_modified15|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_B15_16|44.544039/330.000000|A_HEAT_REJECTION_SHORTFALL,D_PUMP_NETWORK_SHORTFALL,B_WARM_PIPE_AND_JOINT_PARAMETER_INTERACTION|cause_joint__physical_modified15|49.917578/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "FAIL", "THERMAL_COMPLIANCE": "FAIL"}|缺保证/阻塞|
|ROBUST_C20_02|44.972021/0.000000|A_HEAT_REJECTION_SHORTFALL|cause_capacity__physical_modified20|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_C20_06|44.000054/330.000000|D_PUMP_NETWORK_SHORTFALL|cause_pump__physical_modified20|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_C20_11|44.000054/330.000000|H_OBSERVATION_STALE_F_RESTRICTION|cause_measurement__physical_modified20|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_C20_12|47.563656/330.000000|G_REDUNDANCY_LOSS_OWNER_DESIGN_BASIS_PENDING|cause_second__physical_modified20|43.800054/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "PASS", "THERMAL_COMPLIANCE": "PASS"}|缺保证/阻塞|
|ROBUST_C20_16|44.540624/330.000000|A_HEAT_REJECTION_SHORTFALL,D_PUMP_NETWORK_SHORTFALL,B_WARM_PIPE_AND_JOINT_PARAMETER_INTERACTION|cause_joint__physical_modified20|46.365768/330.000000|{"90S_CONTINUITY": "PASS", "HYDRAULIC_COMPLIANCE": "PASS", "OEM_EVIDENCE": "OEM_NOT_VERIFIED", "RESERVE_RECOVERY": "NOT_RUN", "SAFETY_CORRECTNESS": "MODEL_VALIDATED_CAUSAL_AND_FAIL_CLOSED", "SOURCE_RECOVERY": "FAIL", "THERMAL_COMPLIANCE": "FAIL"}|缺保证/阻塞|

## 原5失败与因果链

五项身份逐一见original_five_failures.json：冷源能力×0.8；源H0×0.97；观测延迟1.2s；接管中W2在60s再失效；联合不利角点。能力/曲线/观测变更从t0即存在，W1在30s失效，不可把所有变化都说成30s注入。每项有同输入单变量反事实及新物理方案；取消二次故障只是必要性反事实，不是硬件修复。
容量不足→罐耗冷→温度/取备用动作→可能负荷侧停流；源曲线不足→实际交点不足330→冷返资格失败；过期观测→冻结M1/独立保护正确拒绝→不能获得连续供冷资格；二次失效→无可用源→库存继续消耗；联合角点保留全部同时输入，不拼接单轴极值。具体第一违规时间、排热、泵/阀和库存曲线均在原始追溯矩阵。

## 联合候选及残余失败

[
  {
    "candidate": "B",
    "tested": 17,
    "failed_ids": [
      "robust_B__02",
      "robust_B__04",
      "robust_B__06",
      "robust_B__11",
      "robust_B__12",
      "robust_B__13",
      "robust_B__16"
    ],
    "status": "NOT_VERIFIED",
    "scope": "Only these17 finite injected conditions; no continuous probabilities or OEM qualification"
  },
  {
    "candidate": "D",
    "tested": 17,
    "failed_ids": [
      "robust_D__04",
      "robust_D__12",
      "robust_D__13"
    ],
    "status": "NOT_VERIFIED",
    "scope": "Only these17 finite injected conditions; no continuous probabilities or OEM qualification"
  },
  {
    "candidate": "E",
    "tested": 17,
    "failed_ids": [
      "robust_E__04",
      "robust_E__13"
    ],
    "status": "NOT_VERIFIED",
    "scope": "Only these17 finite injected conditions; no continuous probabilities or OEM qualification"
  }
]
不是所有双故障都已被业主列入设计基准；本轮把单故障、维修/维护、接管中再故障、源总管/负荷总管共因风险分别保存。不得自动套TierIII或作认证。若没有所有要求均通过的候选，结论NO_FEASIBLE_CANDIDATE，不把安全拒绝当冷却PASS。

## 16项答复与决策边界

1/2. 两组原17中的5失败、精确ID/参数/hash及直接原因见首表与JSON，包含初始条件、故障窗口及后续次生事件。
3. 项目控制可改进实际Ready准入、测量过期拒绝、设计流量不足的备用源接管及零速/闭阀顺序；冻结M1完全不改。1.2s链路不能靠放宽1s有效期修好；更快独立测量链是新增硬件假设，原慢链不用作有效数据。
4. 能力/泵交点不足、预冷缺失、双源失效及负荷共管失效需相应物理改动。备用泵升速/整套源接管可能消除部分问题，但必须看实际联合输出，不能靠软件创造冷量或无缝切罐。
5/6. 15m3罐是否继续使用取决于实际冷量/分层与本次全部网格。85pct真实初始量≠17TT能保守证明85pct，更不等于旧4TT可证明；本轮90pct候选以17TT、0.2K拟议不确定度做保守估计，单调温层及未测区域须FAT实证。回充后的真实层状态再放冷已单列，不能手工重置成理想85pct。
7/8. 已模拟A独立小循环与C独立冷服务/HX，泵/阀/测点/电源全部列为新增；B专用旁通因路由/隔离缺资料NOT_RUN。不能推荐凭空已有的旁通。A设备少但依赖同一湿源；C隔离较强但增成本/冷服务/COP和电源依赖，最终需施工图及OEM证明。
9. 模块退出按真实并联支路减少而非只减平均kW；4模块各82.5m3/h、每模块>=约679.038kW只是必要下界。MODULE_FAILURE结果同时展示容量、压降、剩余四模块与切备用整套，需风机/喷淋/盘管map证明。
10. PUMP_FAILURE比较3pct退化的速度补偿、V9/R10上限、单泵退出及备用泵；真实流量和泵热独立复算。额定电机kW不能替代Q-H；静压/NPSHr/弱件MAWP与水锤未知，R10<=18m不能靠提高H0绕过。
11. 第三源W3在模型中是新增独立源及其独立接口；源总管故障只在W3独立源侧接口假设下可隔离。共用负荷总管故障仍可能不能由源冗余解决，需要真正独立负荷供液通道/电源/控制域与业主可靠性基准；不掩盖。
12. VALVE_FAILURE明确A隔离需求/PLC请求B、实际卡阀与物理流量后果，独立断言没有需求就报测试失败；假开反馈用实际流量复核。即使不卡阀，当前单负荷选择器break-before-make也可能短时断330，不能用“安全切换”冒充无缝连续供冷。
13/14. 最少修改和最低残余风险不是同一指标。保留A、只加预冷B、预冷+分层C、预冷+能力/泵D、加强隔离E逐一实算，最终三个候选见下；没有价格/map/概率，不声称经济全局最优或风险量化排名。
15/16. 可立即发supplier_RFI_FAT.csv及中文分层FAT/SAT规范要求报价/保证；COMPONENT_FAT只约束本体，90s完整系统连续性归INTEGRATED_FAT/SITE_SAT。所有保证/签章空缺，厂家试验NOT_RUN；协议精度、采样和稳态条件待双方确认，不冒充正式标准。

## 最终OPTION A / B / C

- OPTION A：尽量保持00/01数量及15m3，最低必要能力补强；无真实预冷/库存/流量证据时不能通过。对应option_A及D补强对照，不自动更改客户方案。
- OPTION B：90m3/h独立预冷+拟议100kW热能力、90pct初充、17TT/快测链、合成能力×1.15/速度裕量3pct/备用泵；对应D全17。仍须OEM共同工况、压力与故障隔离证明。
- OPTION C：对应E，增加W3独立源/源侧接口/预冷和20m3罐；独立RC回充另列500/1000kW+330泵试验。负荷总管与执行器共因风险不能因第三源自动消失。

## 完成状态

SOFTWARE_EXECUTION_STATUS=COMPLETED_SOURCE_BOUND_DEVELOPMENT；PHYSICAL_MODEL_VALIDITY=EQUATIONS_VERIFIED_WITH_UNCALIBRATED_ASSUMPTIONS；FAILURE_CLOSURE_STATUS=PER_CASE_PARTIAL；ROBUSTNESS_STATUS=见17项分表；VENDOR_EVIDENCE_STATUS=OEM_NOT_VERIFIED；CUSTOMER_DESIGN_APPROVAL_STATUS=NOT_APPROVED；PROCUREMENT_RELEASE_STATUS=BLOCKED。
保留原C3-C、M1和全部历史证据。没有正式资格、硬件控制、生产、采购或Phase6授权。真实成本/年度性能/概率缺失时只列CAPEX/OPEX变化项，不编采购价和节能率。
