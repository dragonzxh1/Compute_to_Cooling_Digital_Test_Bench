# Build005 三个长案例的完整 selected-prefix 回读

执行：[run38269665488](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38269665488)，
冻结执行 source `9b487ce88143b5bd8f6f537af9f7b2629fa4e27f`。
本报告是后续文档提交；没有修改本轮 candidate、adapter、fixtures、expectations、timers 或 profile。

| Case | Selected prefixes | Complete frame pairs | Native batches/stages | Raw captures |
| --- | ---: | ---: | ---: | ---: |
| ITQ-49 (065) | 152/152 | 11,637 | 28/29 | 116 |
| ITQ-50 (066) | 152/152 | 11,637 | 27/28 | 112 |
| ITQ-51 (067) | 152/152 | 11,637 | 28/29 | 116 |
| Total | 456/456 | 34,911 | 83/86 | 344 |

下载三个完整 artifacts 至仓库外 D:/Github/c2c-m1-remote-evidence/run-38269665488/。
对每个 case 独立核验冻结 plan SHA、15 个 prerequisite 文件哈希、精确 selected inventory，
并逐项确认 prefix 从 t0 回放、行数和结果完整。原始参考/候选轨迹的 966 个完整 canonical
frames 从压缩成员逐帧回读、核验含 LF 的保存哈希，再重算不含 LF 的 canonical 哈希，
与全部 34,911 对 prefix row receipts 比较；无差异。
完整经典 JSON 和 frame 文件 RAW hashes 同时核对，不是仅检查相同的两列声明哈希。

344 个 stdout/stderr/verifier raw captures 和 86 个 stage result receipts 回读一致。
所有实际 Python PID/Job membership、CPU2500、1024/2048 MiB、EXITED child0、cleanup complete /
active-after-cleanup0 核验通过。各小批次完成不冒充整个 case 完成，最终精确覆盖 152 selected prefixes。
本机仅检查保存的文件和哈希，未运行 Python/native helper/model 测试；CPU/模型时间规则未修改。

三个长案例 PASS 不等于全量 campaign PASS：其余 cases、101 schema 与 final 仍需完整执行。
`FULL_DEVELOPMENT_CAMPAIGN = INCOMPLETE`。原 Startup 49/50 与 versioned compatibility 分开；
PF06 原 scope、历史异步输入因果缺口、T09、不可用的 full P history 和硬件校准限制继续保留。
Formal qualification、production port、Phase6、DSX/Twin 修改均未执行。
