# C3-C v4 draft：只修最终证据汇集

这是未完成准备、未获用户冻结/执行授权的新版本，不是v3运行的补丁，也不是正式PASS。v3原源码、冻结包、授权及run38586777499 INVALID均保留。

核心runtime从v3机械派生：namespace/包路径变为v4，candidate仍 `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`，15项核心文件经反向namespace归一后必须与v3逐字一致。实际修复只在新full workflow的final：除schema/startup/prepare之外，明确下载ref、reference-gate、select、split、prefix和plan，保留各阶段原始native evidence。

`test_delivery_workflow.ps1` 证明旧final输入仅3类、新final输入9类，除此之外workflow无语义变化，且15项runtime/gate/schema/environment源码无语义变化；这是纯文件回归，不是候选资格测试。

`build_draft.ps1` 保留全部755项原保护绑定、四份原规范登记原字节，增加新版本source bindings，生成 `artifacts/m1-c3c-v4-draft/` 与独立开发assembly control。状态必须为 PREPARATION_NOT_FINALIZED，不能把草案、只读运输验证或合成门禁结果当作用户批准或formal执行授权。

后续先完成135个官方旧artifact的独立运输证明、53项受限Job合成检查及新包完整source/input/environment/拒绝门禁回读；再生成一个确切、可审签的最终包和分离的用户批准记录。正式测试必须另获新包授权并从prepare fresh开始，不能借用v3或开发PASS。

原Startup49/50与versioned compatibility、SEM02五项严格P1排除、PF06 original INCOMPLETE、任意POST异常原子性 NOT_PROVEN、T09 HOLD/fullP历史不可用/hardware CALIBRATION_REQUIRED全部保持。Production/hardware/Phase6仍不授权。
