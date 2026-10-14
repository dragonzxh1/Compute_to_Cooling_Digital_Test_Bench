# C3-C 正式 fresh 执行登记

2026-10-14（Asia/Singapore），用户直接批准统一审签页绑定的冻结包、源码及全量 fresh C3-C。批准范围仅为 `M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN`，包含审签页 D1–D4；不是生产、硬件或 Phase 6 授权。

## 唯一本轮执行

- [Run 38566504587](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38566504587)
- 执行源码：`bccff042483d4bbb16ad2a92e2d68f35925182c9`。
- Proposal RAW：`f5666e87ab3991d665d12cd6f913e3ef09c6c98c05acdb87d6f62d3c6c6c8e45`。
- Proposal canonical：`7d233befd38c85046bf8b52920660651ea839e41ad4e0070353b3174749e1e35`。

批准收据、执行授权与 run 登记单独保存在 `artifacts/m1-c3c-v1-authorization/`，不回填或修改已签 proposal。记录收据的后续 Git commit 不是执行源码；GitHub 已确认本轮 headSha 为上述批准 commit。

执行前纯文件核验：710 个本地 source bytes 与另 4 个已冻结 ZIP 中的 native/source entries，合计 714 bindings 全部匹配；proposal RAW/canonical、四项 registration、runner 与环境锁身份均匹配。未在本机运行 Python/native/model。

首次使用 commit SHA 作为 workflow_dispatch ref 被 HTTP 422 明确拒绝，未创建测试；拒绝证据单独保留。重新核验远程专用分支精确指向批准 commit 后，通过分支名提交。全部批准身份保持不变。

## 判定规则

完整登记 101 descriptors / 50 原 Startup，从 prepare 全量 fresh 开始；不借旧 PASS。沿用已签 prefix selector、repeat、schema、source/environment 与资源规则。任一 preregistered FAIL 或完整性失败必须保留证据并 STOP；本轮不得修复再跑取 PASS。

GitHub 绿色不等于最终资格 PASS。结束后仍须独立核验官方 artifact、全部 raw captures / full frames / selected-prefix / repeats / schema、actual Python Job proof 和 cleanup、最后 batch 的执行后证据。

## 不可混淆的范围

原 Startup historical 49/50 与 versioned compatibility 单列；五项 causal exclusions 不算 strict P1 Lane B/C PASS。PF06 原 scope 仍 INCOMPLETE，获批补充需本轮 fresh 证据。任意 POST exception atomicity 仍 NOT_PROVEN；T09 IMPLEMENTATION_HOLD，full P history 不可用，hardware CALIBRATION_REQUIRED。

## 本轮停止结果（2026-10-14）

`INVALID_C3_C_EXECUTION`，`behavioral_adjudication = NOT_MADE`。首个 ENVIRONMENT stage 拒绝，后续全部未运行；candidate 行为测试数为 0，不是 candidate FAIL。

已签环境锁为 Windows image `20261004.326.1`，本次 GitHub setup 原始日志显示 image `20261012.333.1`，这一差异足以触发 `QUALIFICATION_ENVIRONMENT_DRIFT`。失败结果未写完整 actual environment snapshot，不能推断其余环境字段全部相同，也不能直接把新 image 代入后重跑。

官方 prepare ZIP（16 文件，6933 bytes）下载 SHA-256 与 GitHub digest 均为 `0708b67bac637c913f2ffdfe8f16a8746974d9848e18ef4eb4a1f342d36b258e`。ZIP 原样归档于 `artifacts/m1-c3c-v1-authorization/failed_run_38566504587_prepare.zip`。原始 workflow log、解包证据完整保存在 `D:/Github/c2c-m1-remote-evidence/c3c-formal-38566504587/`，log SHA-256 为 `e31f3177512145440c3fa6b77eef4cef22f12a47197b00d94f07cdfd6569ba03`。

独立核验 actual Python PID 1340：ready/proof/release 对应同一 PID 和 proof hash；25% CPU、1024/2048 MiB、4 active-process cap；child exit0，cleanup complete、active0；4 raw captures 回读 hash 匹配。空 raw 输出是本次实际结果，不能填造错误日志；结构化 result.json 保留明确环境拒绝。

另外发现一个独立的错误路径缺陷：`run.ps1:197` 在 ENVIRONMENT 失败没有 `runtime_identity_before` 时仍直接访问该字段，batch_stop 因而记录 `PropertyNotFoundException`。这不消除 worker 原本的环境错误，也不构成 candidate 行为失败；本轮不修复。

源码、已签 proposal、环境锁、fixtures 与预期保持原样。本次正式执行已经 STOP，未重试。下一步需单独进行环境重新登记及执行证据错误路径修订；新确切包获批之前不再启动正式测试。机器判定见 `artifacts/m1-c3c-v1-authorization/failed_run_38566504587.json`。
