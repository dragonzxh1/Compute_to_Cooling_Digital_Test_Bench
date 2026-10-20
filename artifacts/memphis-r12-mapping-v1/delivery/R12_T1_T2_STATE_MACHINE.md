# R12 T-1 / T-2 与共用源泵状态机

本文件是过程验证版本，不是不可修改的施工图。原 R12 文件哈希保留，新图由节点—支路 JSON 同源生成。

## 三层身份

CDU_IDENTITY、PRIMARY_NETWORK_ID、SECONDARY_NETWORK_ID 是不同 Enum。一个单元二次环 A/B 对应 CnnA/CnnB，但不能由这个字母推出一次网和罐。T-2 当前一次 A 时，备用 CnnB 打开自己的 P1-AS/AR，P1-BS/BR 关闭。LP-A 不变，LP-B 无启动请求。

## T-2

OPEN_NEW_PRIMARY → WAIT_SECONDARY_MATCH → OVERLAP_WAIT_FLOW → WAIT_OLD_STOP_AND_REVOKE → WAIT_OLD_ISOLATION → WAIT_NEW_MASTER → COMPLETED_UNIT_INTENT_ONLY。

每次只读取已释放、未过期双通道测试观测。不访问 plant、future command 或 M1。匹配持续时间由逐条有序观测累积，不接受一个外来 stable=true。旧主撤销及停泵零速证明后才请求旧路隔离；旧路实际关到位后才请求授予新主；至少后续一个观测才能证实授予。流量需要新 CDU 一次、二次和六柜各自测量，且图上具备真实启用流路。状态名不代替测量。

缺测、未来释放、非法一次串网、双主、卡阀均不宣布完成，保留现有可用路径并请求独立负载保护。超30s进入 HOLD；本单元软件无法保证未知泵/阀动态下仍有连续供流，不能将 HOLD 当成物理成功。压力跟随调速方式、滤器内部阀组、测量允差/新鲜度的工程定值仍 OPEN。测试用0.5s不是图纸批准值。

## T-1

仅同一次网源切换的终态门禁：新源实际流路/流量/冷返、旧源隔离，CDU身份及一次网不变。不实现冷塔60s建冷等动态，不声称全事件过程验证。图纸允许的同网源短暂重叠与一次A/B并通严格区分。

## 共用源泵分段补冷

WAIT_STOP_PROOF → WAIT_OLD_CLOSED → WAIT_TARGET_PATH → WAIT_ACTUAL_FLOW → WAIT_COLD_RETURN → WAIT_RESERVE_PROOF → TARGET_RESERVE_PROVEN_UNIT_FIXTURE_ONLY。

运行罐的预算许可必须外部独立给出，未提供不能自动开始。全部源泵零速不能用关阀推断。B回充结束只产生 B_RECHARGE_DONE；不自动产生 A_RESERVE_READY、DUAL_RESERVE_READY、SECOND_FAULT_QUALIFIED。R-2回A时同序反向，净冷量与泵/塔能力留待动态验证。440m3/h及3.62MW不作为实测性能或默认设点。

## 不确定管线

PID-005 疑似中间贯通线没有作为实际旁通加入。当前图表达“泵→过滤→板换”的文字意图；过滤器 SERVICE 仅为模型支路可用性，不是已批准的实际阀位。设计方可在新验证图中确认/修订；确认前动态 admission 为 PARTIALLY_MAPPED_BLOCKED。
