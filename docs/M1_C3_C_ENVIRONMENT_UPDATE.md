# C3-C 环境更新：实际分配问题

## 结论

仅把锁定版本从旧镜像改成新镜像，不能保证 GitHub 分配到该版本。两次独立运行证据已经显示，新旧镜像同时存在于 `windows-2022` 池。本次没有 candidate FAIL，也没有正式 qualification PASS。

| 本轮 | 实际分配镜像 | 锁定镜像 | 结果 |
| --- | --- | --- | --- |
| 正式 run 38566504587 | 20261012.333.1 | 20261004.326.1 | ENVIRONMENT INVALID，行为测试未运行 |
| 开发环境核对 run 38567914749 | 20261004.326.1 | 20261012.333.1 | ENVIRONMENT 拒绝，51 项合成测试尚未开始 |

第二轮已记录完整实际环境；除 `image_version` 外，其余六个锁定身份字段（Python、系统、Windows version、架构、image_os、全部依赖版本）与新登记逐一匹配。第一轮只有 setup log 对新镜像的明确证明，不补造第一轮缺失的完整实际环境快照。

[GitHub 官方说明](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners)明确：镜像软件每周更新，部署过程持续数天。两次实际分配记录与此一致；`windows-2022` 的 OS 标签不等于某个唯一周构建身份。

## 已完成但未验证的修订

新命名空间 `v0_2/tests/tools/m1_c3c_v2/` 保留 V1 不动，仅增加新版精确环境锁、被拒环境差异记录和 INVALID 错误结果的安全读取。数学核心、candidate、全部冻结测试与预期、profile、Contract14/15/15A、Safety 均未改。

本次身份为 source `970ef7f2af212000dd5035f385351413bea54faf`，control `832343c1006c58a7f0c4b8560ec65a4e242494d53f598b4051de37b1c76b4b53`，runner `45d56843b8f34c75a6442211431d0f4dd5848acb696117a8084b39c2caa305f9`。已保存这一开发 snapshot；未把它宣称已通过合成验证。

## 证据保留

官方 artifact ZIP 独立下载 digest 与 GitHub 一致：`2eac7b72ece430741e9d9da4766a9fc8f4502559fe65235ec3ea496b730b1ca0`。副本位于 `artifacts/m1-c3c-v1-authorization/environment_probe_38567914749.zip`，完整日志/解包位于 `D:/Github/c2c-m1-remote-evidence/c3c-v2-environment-38567914749/`。actual Python PID1116、25%CPU、256/512MiB、ready/proof/release 及四项 raw hash 已独立核对；child exit1，cleanup active0。

## 必须明确的下一项决定

建议登记**两个具体镜像** `20261004.326.1` 和 `20261012.333.1`，不是接受任意 latest；其余六项运行身份仍逐项精确匹配，每个 Job 执行前后仍必须完全相同。最终证据按实际镜像逐 stage 记录，未知第三镜像立即 STOP，不宣称未经执行的全案例跨镜像等价性。

这改变已签“唯一镜像”的环境接受政策，因此目前只提出，不擅自实施或重跑。另一个选择是独立固定镜像执行机，但不能擅自付费开资源或把本机用作 executor。用户决定后才生成新的版本化登记、验证修订并准备新确切执行包；V1 已签包与失败记录不修改。
