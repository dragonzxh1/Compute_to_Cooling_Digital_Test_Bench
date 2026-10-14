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

当前结果：`PENDING`，`behavioral_adjudication = NOT_MADE`。运行完成并独立回读前不发布资格结论。
