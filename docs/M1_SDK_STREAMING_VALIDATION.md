# SDK 长输入修复：完整开发验收通过

2026-10-14，状态：INSTALLED_FULL_101_INPUT_DEVELOPMENT_VALIDATED。

[run38493762797](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38493762797) 的11个独立安装组全部结束，并已下载官方ZIP逐一匹配GitHub摘要；不是只看绿色。source9f0b2e87a7c324a841274bc92303b009fbebbb63；SDK source80fa3e17af9b6e624d2a6f42ecd103d78fa5fa63；外部可信ZIP SHA256=820baee49b3170dc07bc7bb6bfa3ffdc9732c9c79492ccc7df43699202e6bf78。

| 独立回读项目 | 结果 |
| --- | --- |
| exact输入union、完整row_count及原input hash | 101/101、3216拍，无遗漏/重复/旧PASS拼接 |
| 每输入完整reference和V4 split帧 | 6432份逐一解压核对SHA，全部与已独立核验的V4 full campaign同帧原字节一致 |
| trace/document/journal/progress | 707文件长度及SHA匹配；offset连续、帧数完整，无裁剪历史 |
| 安装与源码 | 各组675payload哈希检查；91本地source bindings匹配；实际V4导入路径在checkout外SDK |
| 独立比较 | 全部输入18条原CMP规则PASS，原数值/预期/比较器未改 |
| 执行日志/环境 | 44raw captures；11组Python3.11.9/Windows2022 image20261004.326.1，依赖锁前后不变 |
| actual Python Job | ready/proof/release实际PID一致，Job身份/25%CPU/1024与2048MiB/480s/cleanup active0全部核对 |

完整canonical documents仍落盘，CPU/内存/模型time规则不变。最长组约200.187s。分组只重置独立用户CLI调用上下文，不给tracking新grace、不裁历史、不更改fault criteria。UUID只是存储目录身份；同输入完整帧跨独立campaign一致，未把旧成绩作本次运行结果。

旧run38492275799的MemoryError和旧ZIP保留。该故障是SDK同时在RAM保留多份完整历史并序列化产生临时副本；新入口使用原有流式trace和immutable journal。以前只验小例子不够，现在长输入完整使用路径已有实际证据。此证明不覆盖任意未来输入长度、其他操作系统、实际硬件或本机硬挂根因。

纯文件reader初次因最后artifact尚未下载而停止；后续汇总遇PowerShell property集合Count错误。只修新reader的汇总写法后，从头完成文件审阅。没有重跑远端考试、修改candidate或预期。证据摘要：[M1_SDK_STREAMING_READBACK.json](M1_SDK_STREAMING_READBACK.json)，reader：v0_2/tests/tools/m1_release_review_v1/verify_sdk.ps1。

开发完成事实分列：完整V4 campaign101/101、2281prefix、499快照、101schema已独立PASS；安装后101完整输入也已PASS。原Startup仍49/50，versioned compatibility单列PASS；五个因果排除仍INCOMPLETE，PF06原scope INCOMPLETE、补充待审批，T09 HOLD、fullP history unavailable、hardware CALIBRATION_REQUIRED。

正式C3-C尚未执行。用户要求先完成开发、再正式测试和冻结审签；下一步是新、独立、hash-bound formal执行/审签包，不改旧DEVELOPMENT guard或将成绩改名为qualification。
