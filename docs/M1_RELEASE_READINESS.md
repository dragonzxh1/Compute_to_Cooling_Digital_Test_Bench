# M1 上线目标：当前交付与未关闭项

2026-10-16更新。原目标保持：解决所有阻塞、达到可上线版本要求、交付使用说明与参数意义、跑通正式C3-C。限定软件域已通过正式资格，不等于原始完整M1范围或生产上线已完成。

## 已有可交付内容

| 原要求 | 当前事实与证据 |
| --- | --- |
| 实际实现和发布故障修复 | v4 candidate `70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`。POST登记切点修复、完整开发campaign及安装后完整输入已有独立回读；任意异常原子性不扩大证明。 |
| FR03 / FR05 / PF16及正式设施 | 101个descriptor adapters、适用同步因果域的独立PRE/Safety/PLC/POST比较、18 CMP规则、56字段、schema、source/environment/Job/raw/cleanup完整验证。原PF矩阵15项满足，PF06通过单独批准C8补充域；五项SEM02不授strict P1 PASS。 |
| Fresh正式C3-C | 唯一run38833878662：101案例/3216行、499快照、2281prefix/67575帧对、101 case schemas、969静态stage+动态阶段+FINAL，独立回读通过。原Startup49/50和versioned compatibility PASS分开。[正式结果](M1_C3_C_V5_FORMAL_RESULT.md)。 |
| 仓库外安装及长用法 | 原source SDK SHA `820baee49b3170dc07bc7bb6bfa3ffdc9732c9c79492ccc7df43699202e6bf78`；run38493762797在新venv、checkout外执行101完整输入，6432帧、707trace文件和实际Job/cleanup独立核验。[安装记录](M1_SDK_STREAMING_VALIDATION.md)。这是development验收，不是CLI正式资格。 |
| 使用说明与单一交付入口 | [RC1先读说明](../artifacts/m1-offline-delivery-rc1/README_FIRST.zh-CN.md)连接使用指南、37类/259字段参数参考、确切SDK、v5正式manifest/授权及结果。原SDK与冻结文档字节不变，当前状态由外层说明更新。 |

## 实际交付包

[M1_OFFLINE_DELIVERY_RC1.zip](../artifacts/m1-offline-delivery-rc1/M1_OFFLINE_DELIVERY_RC1.zip)，2,269,187字节。

- ZIP SHA-256：`8a268066e4b108da8c30d26778bbcfc619e4d9b6c6a8bcb36610c97498d5b86d`
- RELEASE_MANIFEST.json RAW SHA-256：`535536aa9826595c2b35507b66051028fc57ec63dba42584b6b21319c7f1ee32`

两个全新目录纯文件组装得到相同ZIP哈希；40个载荷从ZIP独立回读核验。836项源码绑定组装前后不变。SDK的675个manifest payload逐项长度/哈希通过；与v5 formal closure共有671路径，670完全相同，唯一差异为保留的旧说明快照，无runtime代码冲突。SDK额外CLI等文件不自动获formal资格。

本次只做文件组装、ZIP/hash/JSON审阅，没有本机Python/native/model运行，没有重开开发或正式考试。构建器最初短函数名H与PowerShell Get-History别名冲突，预检即停、未产生交付目录；仅修未封存的纯文件构建器名称后完成两次fresh组装。不是修改candidate或在同一次formal执行内修复取PASS。原失败证据与v3/v4 INVALID均保留。

外层状态为 `PREPARED_FOR_USER_DELIVERY_REVIEW`，不是自动签署的生产发布；未创建GitHub Release/tag，未部署。

## 完整目标的保留限制与授权边界

范围解释：SEM02五项、原PF06和完整P历史的排除已由限定范围收据批准；不要求为了交付限定离线软件而把它们改成PASS，也不重复申请已批准的v5冻结/正式执行。下表说明完整目标仍未覆盖什么，不是把这些历史限制重新变成限定域的代码缺陷。当前待用户明确的是“离线软件正式发布”还是“进入新的真实系统上线准备阶段”；后者涉及未授权的M2/M4/M5义务，不能由M1成功自动启动。

| 未满足的完整范围义务 | 为什么仍未关闭 | 需要什么，不能做什么 |
| --- | --- | --- |
| SEM02精确五项strict P1 Lane B/C | 一个历史异步trace缺独立过去签发证明，四个输入为非法/拒绝域；兼容或拒绝通过不创造同步因果资格 | 恢复真实独立来源并另行登记，或由用户保留排除范围；不能伪造PLC/Safety收据或改判P1 PASS。 |
| 原PF06 scope | 原来源不满足非空前提；新C8补充已获单独formal验证，但不是改写原C3-A | 原scope保持INCOMPLETE。需原来源真实证据或另行批准范围修订，不能将补充成绩覆盖原结果。 |
| 通用异常/物理重启恢复/硬件校准 | 任意POST、OS crash及掉电原子性NOT_PROVEN；T09物理持久恢复IMPLEMENTATION_HOLD，真实硬件CALIBRATION_REQUIRED | 单独授权语义、实现与硬件验证；现任务禁止更改冻结contract/Safety或真实控制，不能靠离线fixture PASS豁免。 |
| 完整P历史与本机安全性 | 完整P历史不可用；本机整机硬挂根因未获关闭证明 | 真实历史材料和独立主机诊断证据是外部条件。远程通过不是本机稳定性认证；本机Python/model/native压力执行禁令保持。 |
| 生产/硬件/Phase6与外层分发决定 | 用户已授权确切v5 executable freeze及formal执行，不等于现场部署权限；外层RC1未单独批准正式分发 | 可审阅并明确接受限定离线交付；扩大到生产/硬件/Phase6必须单独授权，不能自动继承。 |

原始M1全范围状态仍为 `M1_DEVELOPMENT_COMPLETE_SCOPE_INCOMPLETE`；新限定软件正式gate为 `C3_C_LIMITED_SOFTWARE_QUALIFICATION_PASS`。两者并列成立。

当前没有证据支持“所有阻塞已清零、可直接接管现场CDU”。下一步需用户决定交付/扩展范围，不再重复本次已完成考试，也不通过降低原要求来宣布目标完成。

早期开发、安装失败及修复过程保留在原版本证据和Git历史中；本页是可变进度入口，不回写历史运行结果。
