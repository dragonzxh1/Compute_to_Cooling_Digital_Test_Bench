# Memphis inverse engineering sizing v1

用户本轮授权专用分支提交、推送、隔离远程开发测试；不合并、不发版、不运行正式C3-C。

入口为hash-bound GitHub workflow `memphis-failure-closure-v1.yml`，不是本机Python命令。所有数值导入必须在实际PID通过外部Job核验后；CPU25%、1024/2048MiB、每阶段480s、源前后核验和退出cleanup为0。

`registration.json`是客户硬限、扫描、拒绝、网格、联合角点的预登记。`requirements.py`求必要守恒下界与冷源温度/流量曲面；`buffer.py`独立A/B罐网格/混合/壁热容试验；`precool.py`求有热增益及泵热的闭式预冷回路条件；`stages.py`调用原正向求解器，扫描所有观测到的pass/fail边界并局部细分，不假设单调性；`report.py`形成参数矩阵、可行域、Pareto及一个整合报告。

设备“最低性能”只在明确的模型、离散点和未标定假设下有效。实际空气侧UA、风机/喷淋功率、COP、罐壁/布水器、保温、OEM泵曲线、NPSHr及静压/水锤不能从单工况反求唯一值，必须为空或条件区间。整合正常干冷组保留热工模型的热工网络68.37二次流量；正常49.19另用原设备模块边界fresh验证，不冒充完整正常工况水力保证。

原V2、Failover V1和M1/source/fixture/contract全部保留；仅新分支CI门禁增加本分支排除，旧CI原字节快照保留，数学/期望无例外。us_project_unit6_v1/us_project_dynamic_v4通过原project.json、model.mjs及既有端口谱系复用，不宣称重新开发或厂家标定。
