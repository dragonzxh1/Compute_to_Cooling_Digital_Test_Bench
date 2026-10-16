# 六柜 GB300—M1 离线闭环开发 MVP v1

状态：源码实现中，尚无本版本远程运行结果；不得仅凭代码或历史 C3-C 标成通过。

范围：六个独立负载 ID、一个二次泵、六条并联阻力路径、一个 CDU 换热器、供液/回液/六柜液体库存。直接将95%IT功率注入对应机柜液体，余下5%单列空气热量；**没有芯片结温或冷板模型，不能证明 GPU 安全**。一次入口为规定37℃边界，不宣称冷塔/水箱全站闭环。

## 运行

本机有硬挂历史，禁止在本机运行 Python/native/model。只用新的 GitHub 专用分支和 `gb300-m1-six-rack-v1.yml` 开发工作流，绑定 exact commit 和 source_manifest.json RAW SHA256。远端 Python3.11.9 使用原依赖锁；每阶段 Windows Job 为 CPU25%、进程1024MiB/Job2048MiB、480秒，外部核验实际 PID 后才释放工作负载。不要运行旧 formal 或 campaign。

远端顺序：NEGATIVE（新负测+原水力基线一次）、LOAD_STEP、PUMP_STUCK、两个独立重复、0.05/0.025秒细化，最后纯文件审阅。失败保留原始 stdout/stderr/Job/源码身份，不修改冻结 M1 取 PASS。

源码只放新集成目录；旧 GB300 v8/动态 v4 不修改。`bound_project.json` 是项目参数的原字节来源快照。复用 v0.2 的泵执行器、水力求解、泵能量和逆流HX；M1直接使用冻结 `m1_engine_v4.engine.SplitEngine`，candidate SHA256必须仍为 `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`。

## 参数与时间

`scenario.json`：6个独立的W负载在10秒从25%升至90/95/100%；120秒情景；物理步长0.1秒，控制/采样0.2秒，测量延迟0.1秒。转速均为fraction，不是RPM；压力是Pa差压，不是绝对压力；温度内部K、报告℃。各参数出处、派生公式和未标定项见 `parameter_provenance.json`。UA220kW/K、泵曲线形状和等阻力支路是敏感性假设，不是厂家数据。

M1 frozen profile保留原字节；本次新增0.1秒测量延迟属于新集成工况，不冒称已包含在旧资格域。旧profile的转速范围/执行延迟/一阶滞后/斜率全部照用。反馈控制以已发布机柜回液温度形成泵速请求，M1只监督，不产生请求。

每一逻辑时间先推进旧物理区间，再发布已到测量、M1 PRE、独立Safety commit、控制器与模拟PLC签发、M1 POST，最后保存；负载突变只影响之后的区间。时间戳整数ns，禁止预看新命令或未来负载。初始泵速是显式物理初值，不伪装成历史PLC执行证明。只有真实调用原SimulatedPLC.issue产生的token能被M1接受；每次只供应当前控制器选出的一个值，不传未来调度表。原token仍保留FIXTURE_EXOGENOUS_COMMAND_VALUE，其新增反馈选择逻辑不继承资格。

## 两场景和结果

- LOAD_STEP：正常泵追随反馈；检查负载→热量→测量→命令→实际转速→水力→温度。
- PUMP_STUCK：10秒后只冻结物理转速，ready/fault位保持健康；命令队列照常接收，M1根据独立已发布测速判定。报告各状态实际首次出现时间；某状态可以不出现，不强造TRACKING_PROGRESS或固定时刻确认。
- Safety只用独立温度/压差/流量/传感器通道及M1 contribution；不调用旧Supervisor的第二套tracking计时器。压力优先；FAULT无自动清除；热通道独立迟滞、2秒驻留与5 distinct恢复样本。PERFORMANCE模式只记录降载请求，不篡改IT轨迹；不假设备用设备。

每案输出 `series.json`、`physics_intervals.json`、`measurements.json`、`phases.json`、逐时间序列 `events.jsonl`、完整M1事务压缩日志与索引、能量/质量账本。统一 `engineering_report.html` 给两案温度/转速/流量/压差图，JSON给判定、重复性、收敛和5类原因；`artifact_hashes.json`登记实际字节。所有阶段及证据齐全才可给INTEGRATION_MVP_PASS，否则INTEGRATION_MVP_INCOMPLETE。

保留 C3-C v5 原结果；NEW_INTEGRATED_SYSTEM_QUALIFICATION/PRODUCTION_IMPLEMENTATION/REAL_HARDWARE_CONTROL/PHASE6 均为NO。
