# Memphis R12 拓扑与阀序映射 V1 交付入口

最终执行：`ecc4851e7f4616c09a3eed8476e15a53ce3661c7`。
[官方开发 run39452435236](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39452435236)：35/35静态/合成单元用例通过。不是动态、OEM或工程批准。

主报告与全部要求的登记表：[交付目录](../artifacts/memphis-r12-mapping-v1/delivery/)。请先看 `engineering_report.html`（下载后打开）、`R12_MODEL_MAPPING_REPORT_ZH.md`；图谱、输入/环境/源码哈希和逐条正负向结果在同目录。

## 本轮交付核验

独立下载了官方ZIP，并比对GitHub公布的SHA256；核验31个原始证据文件、16个交付文件、194条SVG/JSON支路、三组全18柜图路；核验T2旧主撤销/隔离在新主授予之前、一次A保持、LP-B未启用。实际Python PID2884在CPU25%、256/512MiB Windows Job中执行，退出后cleanup=true、active=0。环境Python3.11.9，Windows镜像20261012.333.1。原始日志和完整Job证明均在官方ZIP中。

`independent_review.json`、`PACKAGE_REVIEW_MANIFEST.json`及官方ZIP见[证据目录](../artifacts/memphis-r12-mapping-v1/evidence/)。首轮run39450623853的失败ZIP与失败保存核验同样保留，不借其7项PASS作为最终覆盖。中间版本run39450938136/39451963295保留其各自源码和结果身份；最终结果来自fresh run39452435236。

对基准`b9d7dcd9773752910d0cb505f82222e4e657eced`核查，执行版本只增加本R12模块/工作流，并在专用远端分支的普通CI排除表增加本分支。冻结M1、旧CDU模型、其他工程历史、DSX/Twin/workbench均未修改。5份用户原件再次验哈希一致。原R12是可修订的过程图，不是不能改的施工冻结图；修订必须版本化，不能消除来源/设计未决项。

## 仍阻塞动态工程放行

admission=`PARTIALLY_MAPPED_BLOCKED`；`DYNAMICALLY_VALIDATED=NO`、`OEM_VERIFIED=NO`、`ENGINEERING_APPROVED=NO`；`MEMPHIS_ENGINEERING_NOT_APPROVED`。

本轮T2是单元阀序；T1仅同一次网源切换终态门禁；回充是单元序列。没有把冷源建冷、真实罐冷量、回A恢复、双罐90s再资格或第二次完整故障伪装成已完成。PID-005贯通线、泵跟随实现、滤器内部阀组、每CDU一次FT/并流压差链、测量定值、泵曲线/UA、M2冲突均继续OPEN。当前图纸可以据这些问题修订，但不自动构成工程批准。

## 下一轮动态案例/预算提议（未启动、未批准）

|候选|拟物理时长|拟验证价值|前提|
|---|---:|---|---|
|D0单六柜新拓扑基准|30s|先量实际计算成本、核流量/热接口|实现新的动态端口连接；不借旧A/B模型|
|D1 T2同一次A网接管|每例120s；正常/一次缺流/二次缺流/卡阀/过期5例|检验瞬态与单元门禁、每柜流量/温度|压力跟随、测量接口与阀序候选显式登记|
|D2同网T1源切换|150s|30s前段+90s连续窗口+30s尾段|登记源启动曲线及实际冷返判断|
|D3共用源分段补B、回A与再故障|恢复段1800s，另加90s故障观察，最终时间轴另登记|核双罐实际末态及第二次故障|罐/泵/塔性能与运行罐预算机制；独立长程批准|

实际执行时间：目前没有R12动态基准，不能给出可靠分钟估计。先完成D0基准，才可由实测成本提出D1—D3墙钟预算；不沿用从未正式批准的60/105分钟方案。资源提议为CPU25%、进程1024MiB/Job2048MiB、首个基准仍最多480s，全部仅是**下一轮提议**，不得自行执行或延长。若在这些限制内不能完成，应保存失败并重新讨论，不用拆段规避预算。

不含正式C3-C、生产、硬件、采购、Phase6或主分支合并。
