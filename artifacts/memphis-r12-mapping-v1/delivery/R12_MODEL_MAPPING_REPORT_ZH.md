# R12 拓扑与阀序映射 V1

结论：35/35 项静态/合成单元验证通过。不是动态热水力 PASS。总 admission 保持 **PARTIALLY_MAPPED_BLOCKED**，工程状态保持 **MEMPHIS_ENGINEERING_NOT_APPROVED**。

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

- SOURCE_REGISTERED: PASS_ORIGINAL_BYTES_RECHECKED_LOCALLY; HASH_BOUND_INTAKE_USED_REMOTELY
- TOPOLOGY_MAPPED: DECLARED_FUNCTIONAL_INTENT_PARTIAL; PID005_CONNECTIVITY_BLOCKED
- CONTROL_IMPLEMENTED: T2_UNIT_STATE_MACHINE; T1_TERMINAL_GATE; RECHARGE_UNIT_SEQUENCE
- UNIT_TESTED: 35/35 PASS
- DYNAMICALLY_VALIDATED: NO
- OEM_VERIFIED: NO
- ENGINEERING_APPROVED: NO

## 验证证据与边界

正向和负向结果分别见 JSON，含逐观测命令、实际阀/泵反馈、FT、许可、预期/实得、资料依据；均明确 SYNTHETIC_UNIT，不生成 PLC issue 收据。
源参数采用哈希绑定接收层，S5仅结构参考。静态注册数：192组件记录、108端口、194有向支路、166测点。组件含模型过滤器可用性抽象，不是物理采购数量。
基础热接口：18×147.25=2650.5kW，每六柜883.5kW，经所选CDU映射；测试不是UA求解，不含泵热/罐储热，不证明实际冷源容量或完整能量守恒。没有流路时热负载不能消失，应保留未移除热量。
SVG完整支路图谱与JSON逐边核对一致：194条。不是施工CAD；尺寸、管径选择、阀Cv/动作、NPSH、水锤、定压/泄压须专业深化。
本轮CPU25%、单Python进程256MiB/Job512MiB、480s上限；没有本机Python/模型运行，没有1800s仿真，没有采用60/105分钟预算，没有正式C3-C/生产/硬件/采购/Phase6授权。

## 下一轮候选（未启动、预算未批准）

先定义压力跟随与滤器内部可施工阀序；再分开注册单单元T2、同网T1、A运行分段补B/返回补A及真实末态第二次故障。物理时长先围绕切换窗口逐例登记；1800s恢复仍需独立预算。执行耗时无R12动态基准，当前不虚报分钟估计。保持CPU25%和已批准内存上限，若动态模型需提高则另请批准。

## 来源与执行

执行commit：ecc4851e7f4616c09a3eed8476e15a53ce3661c7。Python：3.11.9。镜像：20261012.333.1。
源码、输入、共享监督器与工作流原始SHA256：R12_SOURCE_INPUT_ENVIRONMENT_MANIFEST.json。全部交付字节：R12_DELIVERY_HASHES.json。
