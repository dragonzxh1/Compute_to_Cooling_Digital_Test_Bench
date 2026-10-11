# Remote recovery smoke v1

2026-10-12 用户授权：上传必要恢复文件，在独立 GitHub 托管 Windows runner 执行环境检查和小案例。不是 formal C3-C / M1 campaign / production / hardware / Phase 6 授权。不在 HIPPO 执行 Python。

## 发布与身份

独立 worktree / `codex/liquid-recovery-remote-20261012` 保存完整必要源码与依赖。原开发目录与原失败证据不改。无 DSX、无临时日志批量提交。`source_bundle.zip` 保存原 68 项 source inventory、inventory 自身以及既有外部 native helper/验证器的精确 bytes，避免 Git 换行处理改变原 hash。源码仍以文本提交便于阅读，执行权威 bytes 为绑定 SHA 的 bundle。此包不是整段旧历史或完整 M1 fixtures 的恢复。

默认分支只登记 manual workflow 入口；开发包在独立分支。提交 `[skip ci]` 跳过原 push/PR broad CI，只通过 GitHub CLI 单独 dispatch 此 workflow，绑定 exact commit / execution manifest / runner hashes。没有 PR 或自动合并。Workflow pin Windows-2022、Python 3.11.9、exact declared dependency lock，job 25 分钟，artifacts 7 天；实际 image/OS/host/路径另行登记。

## 执行范围与先后顺序

1. ENVIRONMENT：实际 Python 在 suspended-before-assigned 的专属 Job 中启动，ready/release sleep 握手；外部 VerifyTarget 验证实际 PID 属于该 Job（不要求 launcher PID 等于 Python PID）、CPU 100/10000=1%、256/512 MiB、active limit 4、kill-on-close。实际启动/退出/raw fsync/owned cleanup、依赖与 source 全过后，机械登记新的 generic development smoke 环境，不改原 M1 env lock。
2. THERMAL：原 2 个热节点测试函数、6 个 parametrized cases。
3. HYDRAULICS_TRANSPORT_CDU：原 7 个测试函数、11 个 cases。
4. PHYSICAL_PROBE：原 branch=2 / 5 s / dt=0.1 s 的 50 步账本/日志诊断。
5. SHORT_FEEDBACK：原 3 个短反馈测试，总计原 pytest 20 项，加独立 probe；不跑 120 s sweep。

每项独立 Python 子进程；wall <=120 s，native helper 1 s fsynced heartbeat。回调异常、exit 非零、FAIL/INVALID/INCOMPLETE、source/env drift、Job/清理不完整、raw persistence/hash 错误均首错整批 STOP，不同轮修复不能删除旧失败。无 bool 压力、无长 prefix、无 campaign。pip/setup 只在远端一次性机器上安装，尚未进入模型；安装失败也结束 workflow。

`primitive_consistent` 控制字段仅表示本阶段没有上报 primitive anomaly，不是 primitive 压力证明或硬件稳定认证；没有新的 primitive stress 门禁。

Raw stdout/stderr 在 finally 中 fsync/回读并保存 receipts，然后才解析 structured result。每轮独占目录；START/BEGIN 没有 COMPLETE 是不完整，不因 Actions 表面绿色猜成绩。STOP 后后项 NOT_RUN；kernel interruption可能无法写最终文件，仍不是 PASS。使用 artifact download 查看完整证据，网页 stdout 截断不影响本地 authoritative files。

## 本版本边界

Python smoke 源码不修 candidate/阈值。新 environment registration 明确是 `MECHANICAL_ENVIRONMENT_AND_EXTERNAL_JOB_CHECK_UNDER_USER_REMOTE_SMOKE_AUTHORIZATION`，不是用户对旧正式环境 hash 的替换批准。一般数据适配问题按新版本修复并保留前次失败，不边跑边改 fixture 或断言。

通过只能说明此独立环境中的上述小范围检查通过。Windows-only M1 新环境与 adapter、indices 65/66/92 长 prefix、完整 development campaign 尚未在此执行。旧 Startup 49/50 不回写；Full P history remains unavailable；hardware CALIBRATION_REQUIRED。
