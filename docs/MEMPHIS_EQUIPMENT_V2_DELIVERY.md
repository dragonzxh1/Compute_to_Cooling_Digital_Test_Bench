# 孟菲斯设备验证与故障接管 V2：使用入口及结论边界

这是离线工程开发工具，不是现场控制器。最终结论、数值与独立核验状态以本次交付目录为准；GitHub 绿色本身不是设备或工程合格证明。

## 1. 先看什么

- [中文工程报告](../artifacts/memphis-equipment-v2-delivery/ENGINEERING_REPORT_ZH.md)：单柜/六柜、A/B、90秒、回充、UA、设备与泵冲突。
- [可交互HTML](../artifacts/memphis-equipment-v2-delivery/engineering_report.html)：下载后直接用浏览器打开，不需要启动Python或本机仿真。
- [设备逐参数矩阵](../artifacts/memphis-equipment-v2-delivery/equipment_selection.csv)及[供应商RFI](../artifacts/memphis-equipment-v2-delivery/supplier_RFI.csv)。
- [全部分项等级](../artifacts/memphis-equipment-v2-delivery/engineering_outcomes.csv)、[接管时间线](../artifacts/memphis-equipment-v2-delivery/failover_timeline.csv)、[源泵工况](../artifacts/memphis-equipment-v2-delivery/pump_conflict_curves.csv)。
- [独立核验](../artifacts/memphis-equipment-v2-delivery/independent_verification.json)、[完整身份清单](../artifacts/memphis-equipment-v2-delivery/source_input_environment_manifest.json)、[交付哈希](../artifacts/memphis-equipment-v2-delivery/delivery_manifest.json)。

HTML是本次原始数据的事后回放，不是现场实时监控，不会自行生成新仿真。选择场景，再拖动时刻；事件列表只显示该时刻已经发生的事件。完整曲线与分项等级为事后全时段分析。先看 `G_WET_LOSS` 的A/B实际切换，再比较 `SIX_STUCK_BACKUP`、`SIX_BACKUP_FAIL` 和 `SIX_SECOND_FAILURE`。

曲线按1秒抽样显示，精确峰值和验收按全部0.1/0.05秒物理步核算。18柜图中的流量是源侧流量，不是机柜二次流量。界面v1.1仅澄清此标签并标出实际冷水首返事件；经核验的数值JSON、判据、原官方包保持不变，版本差异与原包哈希记入交付manifest。

## 2. 这次运行身份

执行源码：`6031e0ef7d32bec0109f328f85ebd5dfef8fe048`。

源码清单RAW SHA256：`5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16`。

[官方开发运行39088951176](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39088951176)。正式交付提交在此源码之上只增加报告/证据与审阅工具；数值执行源码不变。固定开发源码引用为 `codex/memphis-equipment-v2-source-6031e0e`，不是正式冻结或生产批准。

[独立纯文件审阅39120606196](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39120606196)，审阅源码6971c80bfd23fb37ea48ab05b66fc098ae9ead89。没有再次执行模型；流式校验15个官方ZIP、2795个raw文件、18,696事务/完成帧、7718绘图点、82个跨审计版本未变物理文件，以及实际Python Job、释放和退出后cleanup。原件00/01重新做本机纯文件散列比对，未上传原件。

最终客户依据为00/01，原件哈希登记在registration及身份清单。R10仅为比较，不覆盖客户批准设计。43项pytest检查、44个新动态/罐场景与4个新鲜历史动态回归分布在50个受控阶段中；不能把这几个数量相加当作单一“合格设备测试数”。最终实际覆盖以独立核验为准。

## 3. 如何复现

只使用远程受控开发流程。不要在此前不稳定的本机运行Python、native或模型。需要新一次开发运行时，使用固定开发源码引用与确切清单：

```powershell
gh workflow run memphis-equipment-v2.yml `
  --repo dragonzxh1/Compute_to_Cooling_Digital_Test_Bench `
  --ref codex/memphis-equipment-v2-source-6031e0e `
  -f expected_commit=6031e0ef7d32bec0109f328f85ebd5dfef8fe048 `
  -f manifest_sha256=5999a50a2e75af1cb25bc46d7374b5e7ec663ee4696390377fed01b4dab28f16
```

此命令会启动新的完整开发计算，并非读取既有结果；此次交付完成后没有自动再次执行。镜像或依赖不匹配会停止，不能删除门禁。每个阶段使用实际Windows Job、CPU25%、1024MiB进程/2048MiB作业、480s上限，保留stdout/stderr、退出码与cleanup。

官方artifact包含raw与compact；compact用于报告，不代替原始M1完成日志。下载、校验ZIP及全部raw哈希、回读因果/Job/cleanup、重新核算守恒并核对绘图数据后，才可标记独立证据核验完成。

## 4. 参数怎么看

| 参数 | 意义与权限 |
|---|---|
| 155kW/柜、95%入液；六柜883.5kW | 客户设计热源，不能把1100kW选型能力当实际注入热量 |
| UA 110/183.30/209.28/220kW/K | 研究输入或准确工况反算需求，不是厂家可用UA；污垢/制造裕量另缺 |
| 49.19/68.37m³/h与371.81kPa | 二次设计工作包络；外部接口需求不能重复计入CDU内部损失 |
| 阀行程5/15s、备用加速0.2/s、液体库存倍率 | 显式工程假设与敏感性；实际设备响应待厂家保证 |
| 330m³/h、90s、罐出口升温≤0.5K、机柜入口≤45°C | 不可为追求PASS放松的客户判据；45°C不适用于回液或GPU die |

更改新版本工程参数需要新的scenario/source/hash身份与相应开发回归。不得修改冻结M1、原fixture/expectation/contract或历史结果来取得PASS。无故障场景不虚构接管通过；故障前冷水不计作0秒恢复；首次恢复不能覆盖末段再次失败。

## 5. 可以指导什么、还不能指导什么

可以比较所声明假设下的换热需求、真实流量/压差、故障动作、温度后果、冷量恢复和敏感性，形成供应商询价/RFI与设计修改优先级。工程FAIL不是执行失败，不能用软件PASS覆盖。

采购和工程放行仍被准确GB300/CDU规格、项目四端温热选型、PG25泵全图、最弱MAWP/NPSH/静压/瞬态、分层罐实测与真实阀泵时序阻塞。18柜组级冷源故障不代表已经穷举叠加二次CDU故障。2小时断水和10分钟UPS覆盖也不是120/240/900秒窗口已经证明的结论。

共享备用CDU及混合冷源只完成受限架构/缺口比较，没有交叉管网动态资格或OEM同工况图谱。费用与风机/全年水耗缺报价及曲线，不能给虚假成本排名。保持原M1历史/兼容性/严格因果边界；本项目不继承正式C3-C资格，硬件待校准，生产/真实控制/Phase6均未授权。

Build1—4的失败/停止原因与源身份保存在 `artifacts/memphis-equipment-v2-review/BUILD*.md`，原官方artifact及本地源快照保留；尤其Build4的GitHub绿色不能覆盖首返计时缺陷。
