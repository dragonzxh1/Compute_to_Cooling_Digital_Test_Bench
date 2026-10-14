# C3-C v3：拟议冻结包操作说明

本目录是用户审签前的静态交付材料，不是已批准冻结或正式 C3-C 成绩。

1. 检查 `EXECUTABLE_FREEZE_MANIFEST.json` RAW=`2828234ca11f2cbe4b1893e43b802bd5144979572cef0df7bbc4dffa115a88e7`，canonical=`d83a7ba989a23d88b3f2ac19eba4b9b74c71f20dab9c81129277577446f8b0f6`。其 bytes 与正式入口使用的 `artifacts/m1-c3c-v3-freeze/executable_proposal.json` 完全相同。
2. 通过 `EXACT_HASH_INVENTORY.json` 核对755项 source closure，以及本目录所有登记交付文件。inventory自身的RAW由独立回读 control 与后生成的 attestation 绑定，不建立自引用哈希。
3. 从独立 GitHub 只读回读 artifact 获取完整 `C3_C_V3_FINAL_FREEZE_PACKAGE/`。它还包含回读结果、执行/交付身份 attestation 和唯一统一签署页；后三者在 commit 固定、读取真实交付 bytes 且进程清理完成后生成，避免 commit 自引用。
4. 核对 attestation 中 EXECUTION_SOURCE_COMMIT 与 DELIVERY_COMMIT；两者职责分开，本版本若采用同一确切 repository commit，会明确记录二者相等，不能将后来分支 HEAD 代入。用户分别填写语义/范围、确切 executable freeze、formal execution 三个批准栏；空白不代表批准。
5. 只有后续用户明确批准确切包与 execution commit、另有 hash-bound 执行授权，才允许从 prepare 全量 fresh C3-C；任何 FAIL/INVALID 保存并 STOP，同 execution 不修复重跑，不借旧 PASS。

完整登记范围：101 descriptors / 3216 rows / 499 planned full snapshots / 969 static stages + FINAL；prefix 按原 mandatory674 与 fresh progress/confirmed union 精确选择，支持 U/ST/C/S/P15 exhaustive prefixes。Prefix数量不能从旧结果复制。

环境只允许 Windows image `20261004.326.1`、`20261012.333.1`，Python3.11.9与全部依赖/其余六项身份精确锁定；每个 Job 执行前后完整身份相同。正式 model stage 原资源政策维持CPU25%、1024/2048MiB、480s；本包只读核验使用256/512MiB、不执行 candidate。不得在发生硬挂的本机运行 Python/native/model。

原 Startup49/50与versioned compatibility单列；五项因果排除不算strict P1 B/C PASS；PF06 original INCOMPLETE，补充C8须fresh验证；arbitrary POST exception atomicity NOT_PROVEN，T09 IMPLEMENTATION_HOLD，full P history NO，hardware CALIBRATION_REQUIRED。生产、硬件控制、Phase6均未授权。

只读回读 PASS 说明签署准备完整，不表示 candidate 资格 PASS。本目录规范范围未增加真实硬件或任意OS/断电原子性保证。
