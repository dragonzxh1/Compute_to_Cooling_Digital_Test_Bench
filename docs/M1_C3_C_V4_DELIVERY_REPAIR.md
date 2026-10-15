# C3-C v4：证据运输修复开发结果

运输修复已通过独立只读验证；新正式包仍 `PREPARATION_NOT_FINALIZED`。原v3 run38586777499保持 `INVALID_C3_C_EXECUTION / NOT_MADE`，未改判、未重跑。

## 已验证

[只读run38671417001](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38671417001)，source `cc17de59bb3fefe9de40ee835552dc01d3134e86`。从原失败run读取135个官方包，原final隔离保留其失败，不伪装成功。原802缺项精确复现；显式加入上游native evidence后，969必需静态ID缺0项。

只读reader验证1969个原阶段Job/cleanup凭据和7876份原raw capture。18项合成正/负检查通过，601项冻结snapshot物化后755项原保护源码匹配。该probe本身没有启动Python/native/model、没有导入或执行candidate。

官方只读artifact ID11944039345，53,355,159 bytes，SHA-256 `02ab5cc4639abff43ba3548e2a63f740bba34b272835326500cc63d78813ca5a`，已独立复算。其native inventory SHA `b8aaa2b16183807c7a01cc2e2bb7c25b2b319449bd744926e3ad893e36bd7d6b`；另外对55,773个导出文件逐项独立复算SHA，读取716个completed batches、1969条stage记录、1399个唯一ID，冻结969静态清单缺0项。这是运输证明，不是对所有模型full frames/schema/repeats的重新裁决。

第一次开发probe38671114932遗漏snapshot物化，被保护源码门禁正确拒绝。失败日志及身份已保留，没有绕门禁或回写旧成绩。新source增加既有受控601项物化，再检查755项原绑定。

## 新正式包草案的修复

`m1_c3c_v4` 是独立机械派生版本，不覆盖v3。新full workflow的final在schema/startup/prepare基础上，显式下载ref、reference-gate、select、split、prefix和plan。去掉新增下载并还原namespace后，与v3原workflow逐字一致；15项核心runtime/gate/schema/environment文件同样逐字一致。candidate仍70bba3...348ce，969项原阶段、原prefix/repeat/schema/门禁规则不变。

当前草案 `artifacts/m1-c3c-v4-draft/executable_proposal.json` 包含793项绑定（初稿792项另增加确切注册入口绑定），四份规范登记bytes不变。它没有获得新可执行包冻结批准，也没有正式执行许可。不能拿本次运输PASS代替C3-C PASS。

## 剩余步骤

1. 在实际受限Python Job中执行新v4基础设施合成/静态检查，不运行candidate。
2. 完成一个确切新包的source/input/environment/拒绝门禁回读及统一审签页，明确执行commit与hash。
3. 用户单独批准新包冻结和新正式执行后，才从prepare开始fresh C3-C；旧v3无效记录保留、不借旧PASS。

原Startup历史49/50和versioned compatibility分开；SEM02五项严格P1排除、PF06 original INCOMPLETE、ARBITRARY_POST_EXCEPTION_ATOMICITY NOT_PROVEN、T09 HOLD、fullP不可用、hardware CALIBRATION_REQUIRED以及production/Phase6不授权均保持。

机器审阅记录：`artifacts/m1-c3c-v3-authorization/development-delivery-failures/38671417001_review.json`；完整官方ZIP在 `D:/Github/c2c-m1-remote-evidence/c3c-delivery-v4-38671417001/official.zip`。使用说明和物理参数含义继续参见 `docs/M1_SOFTWARE_USER_GUIDE.md`、`docs/V02_PHYSICS_PARAMETER_REFERENCE.md` 和 `docs/LEGACY_SCENARIO_PARAMETER_REFERENCE.md`，不修改原冻结文档。
