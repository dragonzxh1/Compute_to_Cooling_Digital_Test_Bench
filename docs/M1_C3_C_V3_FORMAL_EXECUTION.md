# C3-C v3：用户批准后的全量 fresh 正式执行

2026-10-14（Asia/Singapore），用户分别直接批准确切 v3 包冻结和单独正式执行授权。两个独立收据及本轮 run 登记位于 `artifacts/m1-c3c-v3-authorization/`；旧统一审签页、冻结包和 detached 回读证据不回填修改。

唯一当前执行：[run38586777499](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38586777499)。执行源码与原交付 commit 均为 `65300d9cae0df4b918c4e2db39fdfd7b9915976f`，后续记录批准的 commit 不替代此运行身份。

Proposal RAW=`2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7`；canonical=`d83a7ba989a23d88b3f2ac19eba4b9b74c71f20dab9c81129277577446f8b0f6`。Candidate=`70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`；formal runner=`69bc209c18fdc3f0a83c47228cae4e51bdbe76b0250104977da19bfe1c77a4e9`。

执行前复算 RAW/canonical 和 755 个 source bindings，751 本地文件与 4 个冻结 ZIP entries 全部匹配；审签页、attestation 和远程 branch ref 身份匹配。未在本机运行 Python/native/model。

范围保持完整登记的限定离线软件域：101 descriptors /3216 rows /499计划快照 /969静态stages+FINAL，原conditional prefix/repeat/schema规则，全量从prepare fresh开始，不借此前开发或只读回读PASS。各Job只允许两个登记镜像，其他身份精确且before/after相同；资源规则不变。

任一preregistered FAIL、source/environment/authority漂移、raw evidence/实际Job/cleanup错误或其他完整性失败必须保存证据并STOP，当轮不修改后重跑。GitHub绿色不是交付判定：最终必须下载官方artifact并独立核验所有prefix/full frames/repeats/schema/source/环境/Job和最后batch执行后证据。

旧Startup historical49/50与versioned compatibility分开；五项严格P1因果排除仍INCOMPLETE；PF06 original INCOMPLETE、补充需本轮fresh结果；arbitrary POST exception atomicity NOT_PROVEN、T09 IMPLEMENTATION_HOLD、full P history NO、hardware CALIBRATION_REQUIRED。生产、硬件控制和Phase6均未授权。

当前正式成绩：PENDING，behavioral adjudication NOT_MADE。只读闭包通过以及收到执行授权不等于formal C3-C PASS。
