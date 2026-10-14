# 当前上线目标与验证进度

目标保持：解决阻塞，交付可发布的软件版本和包含全部参数意义的使用说明。
本项目当前是offline software test bench，不因这一目标自动获得真实CDU控制、production Safety修改、Phase6或正式C3-C权限。

| 要求 | 当前权威事实 | 完成条件 |
| --- | --- | --- |
| M1-DEF-POST-001 | 旧版3FAIL/1PASS已重现；v4同一4测试全PASS，原受影响23测试亦PASS；官方ZIP/actualPID/Job/cleanup/环境已独立回读 | 已测软件失败路径关闭；完整新版验收不能靠这27项替代 |
| 新版candidate | v3/Build005与55冻结运行源码无漂移；v4只重排POST提交，受影响回归27/27 | 需fresh全量development及安装使用验证，不能直接宣布上线 |
| 完整验证 | Build005旧开发证据有效，但不能用作新修复版PASS | 受影响回归＋fresh完整软件开发campaign；原Startup49/50与versioned结果分开；所有hash/schema/Job/cleanup完整 |
| 来源/资格缺口 | exact五case causal gap、PF06 original INCOMPLETE、T09 durable hold、fullP history不可用 | 不伪造历史issue，不降低冻结期望；范围登记/正式资格由用户独立裁决，硬件不能靠软件测试消除 |
| 软件交付 | 现有v0.2 wheel未打包M1 development tools；M1/公共控制说明和物理参数参考已按源码编写，仍是未执行安装验收的草稿 | 干净snapshot/wheel安装与实际入口验证，完整参数意义/单位/限制、示例、故障处理/版本证据齐全 |

当前行动：优先完成实际错误的failure witness与修复，不再反复仅写语义中立报告。
用户于2026-10-13明确授权远端专用分支提交/推送/开发测试；本机仍禁止Python/native/model压力执行。

已有新开发回归PASS证据见M1_POST_REPAIR_STATUS.md；全目标仍ACTIVE，当前表是进度/验收依据，不是缩小目标或发布批准。

## 2026-10-14 续跑后的实际进展（优先于上表旧进度）

- V4完整fresh campaign和官方证据独立回读已PASS：101案例、2281prefix、67575帧对、499快照、101schema；原Startup49/50及versioned PASS分列。
- 完整native union已核验287个执行任务、715批、1969阶段、7876raw captures、2895次真实V4构造身份及每阶段Job/cleanup/环境；没有借Build005分数。
- SDK在新Python3.11.9 venv、仓库外安装/导入通过；674包内哈希、actualPID2588与Job/cleanup、参数查询和3拍示例独立回读通过。这不是安装后全部长用户工况验收。
- 使用说明、37类/259字段V0.2参数参考及旧YAML参数说明已提供；旧DRAFT和已验证包字节身份保留。

当前尚须完成：扩展SDK安装后长输入/用户用法验收，准确的限定软件发布签署包及用户冻结/资格范围决定。正式C3-C/production/hardware/Phase6不自动执行，不能通过删掉P1/PF06/T09缺口来宣称全部上线。
见M1_V4_FULL_DEVELOPMENT_REPORT.md、M1_V4_FULL_DEVELOPMENT_EVIDENCE.json和M1_SOFTWARE_USER_GUIDE.md。

原安装扩展run38492275799的MemoryError及失败证据保持原样。新流式SDK run38493762797已fresh完成101/101完整输入，独立回读6432帧、707trace文件和11组actual Python Job/cleanup通过；未裁历史、未提高资源/模型timer。SDK长用法在冻结输入/Windows2022/Python3.11.9域DEVELOPMENT_VALIDATED。见M1_SDK_STREAMING_VALIDATION.md与M1_SDK_STREAMING_READBACK.json。

用户已明确要求：先完成开发验证，然后C3-C正式测试及冻结审签。开发层完整campaign/长prefix和安装后完整输入已完成。下一步准备独立formal执行入口与确切源码/输入/比较器/环境/schema/STOP绑定；旧DEVELOPMENT入口与成绩不改名。最终包审签前不正式开考、不自批冻结；production/hardware/Phase6仍不授权。
