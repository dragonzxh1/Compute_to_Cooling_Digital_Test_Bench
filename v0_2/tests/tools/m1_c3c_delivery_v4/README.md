# C3-C delivery v4：开发中的证据汇集修复

当前仅为 DEVELOPMENT_READONLY_EVIDENCE_TRANSPORT，不是已冻结的 C3-C v4 正式执行包。原 v3 run38586777499 仍 INVALID；本工具不补判、不补跑、不借旧成绩。

`native_closure.ps1` 按官方 ZIP digest 读取原始 native evidence，拒绝跨 run、路径越界、冲突字节、上游 STOP、无实际 Job 证明或 cleanup/raw/source/environment 不匹配；保持每个原始文件的字节和来源。先计划、后合并；同路径同字节可去重，冲突绝不覆盖。导出只允许全新目的目录。

`run_readonly.ps1` 在 GitHub-hosted Windows 上验证 hash-bound 开发源码、原 v3 的755项保护绑定，从已结束且失败的原run读取固定135个官方包：原final及134个原来遗漏的reference/reference-gate/select/split/prefix。原final自身失败目录被明确隔离，不伪装成成功batch。先要求旧包精确复现802缺项，再验证汇集后969静态清单和全部带来的native Job/raw凭据。导出的是独立的只读运输样本，不写回原run。

`test_native_closure.ps1` 是小型PowerShell ZIP/JSON测试；不启动Python/native/model，不能替代候选行为测试。18项合成门禁覆盖旧导出反例、完整合并、重复、错误哈希、跨run、冲突、raw篡改、越界、错误源码、缺少权威锁、导出身份，以及实际PID/cleanup/镜像/前后环境/资源/外层收据拒绝。

开发验证入口沿用已注册的 `m1-remote-long-probe-v2-1.yml`，但在新commit下明确命名为只读运输验证；755项原formal源码不包含这个辅助入口，原入口身份继续可从65300d9取回。三个dispatch参数分别锁定开发source commit、readonly_control.json RAW和run_readonly.ps1 RAW。GitHub token只需要contents/actions read。

正式修复还需要：将完整凭据收集接入新的、独立版本化的完整workflow和执行包；保留全部969静态阶段、原prefix/repeat/schema及授权门禁，完成新的闭包/拒绝检查并交用户审签。不得只删除coverage检查，也不得沿用v3授权重考。read-only PASS不等于full frames/schema/repeats独立复判，更不等于C3-C PASS。

所有candidate/math/fixtures/expectations/contracts/profile/Safety及原v3源文件不改。原Startup49/50、独立versioned compatibility、五项严格P1排除、PF06原INCOMPLETE、T09 HOLD/fullP不可用/hardware CALIBRATION_REQUIRED及production/Phase6边界继续有效。
