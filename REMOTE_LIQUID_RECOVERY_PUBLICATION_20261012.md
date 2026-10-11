# 独立 worktree 恢复测试发布（2026-10-12）

用户批准必要恢复文件上传及 GitHub 托管 Windows 小案例执行，并建议独立 worktree。分支：`codex/liquid-recovery-remote-20261012`。原目录继续保持本机 Python workload HOLD；不在本机安装 VM 或重跑压力。

## 本次完整范围

完整现有仓库基线 + 恢复包及完整必要依赖，而非整个本地未跟踪历史的批量上传。原 68 项源码/判据/配置精确复制；73 项 bundle entries 包括 inventory 自身及两个已冻结外部 native helper 的 source/binary。DSX 不新增、不更新；旧失败日志、所有更早 untracked evidence 不批量提交。

Git 存储使用 `.gitattributes` 的 LF 规则；绑定 SHA 的 source_bundle 保留原精确 bytes，是本次计算输入的权威源。独立执行环境身份不改写旧 M1 environment lock。新 remote adapter 独立 namespace；旧 candidate/fixture/expectations/profile/Safety 不改。

## 发布前证据

Git whitespace 检查报告原 frozen environment lock/requirements 的尾部空行。
不修改冻结 bytes；仅对 blank-at-eof 作已知遗留豁免，其余 staged whitespace 检查继续执行。

- Worktree fresh bounded synthetic control-plane checks：29/29 PASS（无 Python/native 启动）。`synthetic-b8bc81df097d4ea28ff38c8af558b119/synthetic_evidence.json` RAW `1ba2f6551a070ae2cd927ea013fb582ab6ad1f2ce4689b6a986a78703bd297a8`。
- 68 项原 source inventory 匹配；source zip 73 个条目逐一 SHA-256 校验；123,494 bytes。
- 新 PS adapter 语法/带空格及尾斜杠 argument quoting 检查 PASS；命名文件 secret-pattern 检查无发现（不是全面安全认证）。初次 quote 检查脚本遗漏 function header 的参数绑定，产生空参数；改用完整函数定义后检查通过，实际 adapter 未因此改动。
- `source_bundle.zip` RAW `0f49f3d8cdb0c52a19dc594f361a77eeb093bab38859a9547c46bb92207a0113`。
- Remote runner RAW `4acd475a80bad58427ebcfe3ef5c4eac1ed3965ebe5e52a3721a6830ab9bf569`；execution manifest RAW `1fcd5d10b60df1b21e8e04d977378a5e335a73483d0d6f2e79fd913098f21f7e`。

代码审阅按 ship 的 scope/证据/命名提交/发布核对进行；项目明确禁止自动 agent delegation，故本轮 inline 审阅，不宣称独立多角色 review。非产品 release，不改 VERSION、历史阶段状态或增加 unrelated skills/telemetry/config。未创建 PR，以免 PR event 触发旧全量 CI。

## GitHub 执行与边界

唯一新入口 `.github/workflows/liquid-cooling-recovery.yml`：manual dispatch，Windows-2022，Python 3.11.9，exact dependency lock，5 stages，原 pytest 20 项加物理 probe，单阶段 CPU 1%/256-512 MiB/120 s，首错 STOP，raw evidence fsync/readback 后 gate。Environment bootstrap 在真实 Job/清理与参数核验后做机械独立登记，属于已批准的 generic development smoke scope，不是旧正式环境 hash 重新冻结。

提交包含 `[skip ci]`，不触发旧 push/PR full CI。仅默认分支登记 manual workflow 入口；恢复包在独立分支，通过 GitHub CLI 精确绑定 commit/manifest/runner SHA 启动。设置 artifact 保留 7 天，预计证据仅小量；不使用 larger/self-hosted runner。

本文件为发布前状态。远端实际 PASS/FAIL/INVALID、run URL 和完整 artifact readback 会另写新结果报告；不得把本文件的合成 PASS 当作实际液冷 PASS。

长 prefix、完整 campaign、formal C3-C、production、硬件和 Phase 6 均未执行；full P history unavailable。故障唯一根因未确定。后续是否推进由 fresh 远端实际 evidence 决定，不继承旧成绩。
