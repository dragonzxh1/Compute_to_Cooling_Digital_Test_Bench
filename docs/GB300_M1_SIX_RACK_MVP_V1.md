# 六柜液冷—M1 闭环 MVP v1：实际结果与运行方法

结论：**INTEGRATION_MVP_PASS，仅离线软件集成开发验证。**

六个负载、一个CDU和二次泵已形成实际因果闭环，不是把各自PASS拼接。复用了v0.2水力/HX/泵执行器内核、另一个对话的客户项目参数快照，以及字节不变的M1 v4 core。没有直接把浏览器规定流量曲线冒充水力闭环，也没有重新实现M1数学。

## 先看什么

下载官方运行的 artifact，打开根运行目录的 `engineering_report.html`。本地独立复核保存的短路径为 `artifacts/six-rack-integration-review/engineering_report_run38882232763.html`，含两场景的温度、命令/实际转速、流量和压差共8张图，完整JSON与限制在页尾。所有数据来自本次运行，不借旧PASS。

- 运行：https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38882232763
- 专用开发分支：`codex/gb300-m1-six-rack-v1`，不合并、不发生产版。
- 实际执行源码：`048ca4f893ee91cb43cc22e23b246a24f3547bef`。
- 实际执行 manifest RAW SHA256：`53d7e97a0c27f6ecf28085e93ed5345bdf440909b1e7e3db33748767edd3f5df`。
- M1 candidate SHA256：`70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`，836项冻结来源绑定全部保持。

## 两个120秒场景

10秒时，六柜功率从每柜38.75kW，变为155/147.25/139.5/155/147.25/139.5kW。入液比例95%，每柜独立ID和热源账本。PUMP_STUCK同时从10秒起只冻结实际转速；ready/fault测量位仍健康。

| 项目 | LOAD_STEP 正常泵 | PUMP_STUCK 静默卡泵 |
|---|---:|---:|
| 末态命令/实际转速（fraction） | 0.706719 / 0.705978 | 0.9 / 0.349494 |
| 末态实际流量 | 53.631 m³/h | 26.550 m³/h |
| 末态实际泵差压 | 228.780 kPa | 56.068 kPa |
| 末态供液/混合回液 | 38.140 / 51.317 ℃ | 37.052 / 54.821 ℃ |
| 最高单柜回液 | 52.137 ℃ | 57.939 ℃ |
| 跟踪确认 | 无误报 | 29.9秒确认，Safety保持FAULT |
| 二次流体储能增加 | 29.213 MJ | 51.361 MJ |

卡泵证据链：28.3秒HANDOFF_PENDING → 28.7秒SUSPECTED → 29.9秒CONFIRMED；没有出现TRACKING_PROGRESS，报告保留null，不强造正常运动。确认时刻由已发布测速、已签发命令和冻结规则产生，不是写死故障注入后若干秒。10秒到28.3秒的差距包含热响应/反馈请求形成足够可观察需求的时间，不能误读为M1内置19.9秒故障定时器。

重要：卡泵供液温度较低不等于系统更好。低流量下回液更热、流体蓄热更多；必须结合流量/转速/回液判定。这也不是GPU芯片温度。120秒有限时域只证明控制链接通；P控制存在目标偏差，**没有证明达到45℃回液目标或已完成控制调优、稳态容量验收**。

## 验证与独立读回

远端NEGATIVE的22项测试通过，包含现有水力基线，以及未来/未到达测量、过期、无效质量、重复ID、错误真实签发回执、非有限值、水力不一致、压力优先、Safety配置和热源/泵热守恒。

每个主场景1200个物理区间、600个完整PRE/Safety/PLC/POST事务、600个唯一被消费测量。两个场景分别独立重复一次，8类输出逐字节一致。正常闭环0.1/0.05/0.025秒细化，末态供液相邻差0.000324/0.000162K，回液差0.000241/0.000118K；流量/差压差也缩小。**本次三档步长收敛检查针对LOAD_STEP，不声称已完成所有故障工况的数值资格。**

主场景总液体能量残差分别约−1.19e−7J和5.74e−7J；最大节点质量残差分别7.11e−15kg/s和3.11e−15kg/s。数值守恒不是物理标定。

独立纯文件审阅核验了516份RAW哈希，并重新检查全部主场景的测量来源、采样/发布/决策时序、PRE旧命令、Safety/PLC/POST绑定、控制请求与已到观测、解析转速—流量/压差关系、逐区间负载与能量账本。七个阶段的实际Python PID、CPU25%、进程1024MiB/Job2048MiB、exit0、cleanup=true、active_after_cleanup=0全部核对。环境Python3.11.9，Windows image20261012.333.1，单子进程480秒预算。

官方artifact ID `12038302964`，285489744字节，ZIP SHA256：
`292197fa4b30259d28228466a7c961778d6f0382332be92d25ab9d36307c1af3`。

官方原始日志ZIP SHA256：
`601f2f87bcd6c77cade7e40b797c80aab4e31190bc509e4c7a41694b86ba81e3`。

工程报告HTML SHA256：`d1a821a53018944b4ea626f924979e9d5b8d57fbc5a266b908f2275fcd57e1bb`；JSON SHA256：`0b4fafa1558bb91e6578c05e5ecdea0a6bb5f6e43f24da56a56c3186658fbc28`。

## 如何再运行

不要在当前有硬挂历史的本机运行Python、native或模型；本机只做配置/源码编辑及文件审阅。在该专用分支使用GitHub Actions开发入口，先核对源码和参数登记。下列PowerShell命令只通过GitHub CLI启动独立远端，不运行本机Python：

```powershell
$repo = 'dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
$branch = 'codex/gb300-m1-six-rack-v1'
$commit = gh api "repos/$repo/git/ref/heads/$branch" --jq '.object.sha'
$manifest = (Get-FileHash -LiteralPath 'v0_2/tests/tools/gb300_m1_closed_loop_v1/source_manifest.json' -Algorithm SHA256).Hash.ToLowerInvariant()
gh workflow run gb300-m1-six-rack-v1.yml --repo $repo --ref $branch -f expected_commit=$commit -f manifest_sha256=$manifest
```

运行前本地manifest必须与分支对应；错误哈希/源码会拒绝。代码或参数变更需新提交与新manifest，并保留失败，不要rerun旧failed jobs冒充新执行。该分支代码推送也会自动触发同一个开发workflow，**已有运行时不要再手动启动**。本次最后的说明/读回提交不启动第二轮，实际PASS身份始终是上面的048ca4f运行。

主要文件：`scenario.json`为负载与时间/热/水力参数；`parameter_provenance.json`说明每类出处；`bound_project.json`为原项目参数快照。`phases.json`查看M1/Safety/PLC链；`series.json`查看实际量与测量量；`physics_intervals.json`和result.ledger核热账本；`m1_completed.zlib`及索引保存完整事务。报告将热容量、执行器跟踪、传感器/可观测性、控制响应、模型参数不确定性分开，不以总PASS吞掉缺口。

## 保留的边界与失败

UA220kW/K是显式敏感性输入，泵曲线是单设计点派生的二次假设曲线，1.3m³液量和管网分配未实测。没有厂家性能保证、GPU/冷板热模型、冷塔/水箱动态、A/B接管、实际降载执行或硬件控制。真实CDU能否选用仍须厂家/现场资料，不能由本次MVP通过替代。

首个工作流启动run38882025872停止于旧登记文件LF/CRLF传输字节差异，**尚未运行模型**。核对JSON内容完全相同后，仅登记原Git LF哈希与原封存CRLF哈希两个确切身份，恢复后仍严格要求原封存字节；未放松冻结源码身份。该失败artifact保留在本地review目录及原GitHub run。首次新增workflow手动dispatch因默认分支未登记返回404，未生成运行；随后只为专用分支启用push。普通全仓CI未作为本次证据使用；后一次冗余CI已取消。

另外，本地Git自动gc报告旧对象 `843de9ee7f8a580883f0776dd6e183b02f08fbeb` 损坏；本次远端提交/checkout与836绑定核验成功。未删对象、未重写主仓库，后续命令仅禁用本次命令的自动gc；仓库健康问题仍应单独处理，不能从这个错误断定硬挂原因。

`C3_C_V5_RESULT=PRESERVE`。`NEW_INTEGRATED_SYSTEM_QUALIFICATION=NO`，`PRODUCTION_IMPLEMENTATION=NO`，`REAL_HARDWARE_CONTROL=NO`，`PHASE6=NO`。
