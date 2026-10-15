# C3-C v5 最终统一审签页

状态：READY_FOR_USER_SIGNATURE。未批准冻结，未授权正式执行，未产生 C3-C 资格成绩。

## 签署对象

版本 C3-C-v5-final-proposal；范围 M1_C3_C_LIMITED_SOFTWARE_FIXTURE_DOMAIN。

EXECUTION_SOURCE_COMMIT：`9ad4b9d1fdab261db9be09b91f261a927d529970`

DELIVERY_COMMIT：`9ad4b9d1fdab261db9be09b91f261a927d529970`

二者职责分开；本次同一确切commit同时含可执行源码和静态交付包。此页、回读结果和attestation在commit固定后生成，存于只读GitHub artifact，不写入自己所属commit，也不采用后来的branch HEAD。

Proposal RAW：`18d54940b672e4ec06b0c0c0a6691cf15219ee96e01b7864b31fe00a1adf23c8`

Proposal canonical：`74bafde655de214ee02b39b1a9c9d23acd0219ce30309afb9ca810c58447246d`

Candidate SHA-256：`70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`

Formal runner SHA-256：`78749fe78a6701ef2fb9157aa648f966bf088615bb39ab8ffb40f4dc02e51363`

Identity attestation RAW：`a4748f75c5d696718384495c47331e38778287be6769854bd9146b5daeae7f71`

Independent readback result RAW：`0c815fe72f66de43c3db60ba1d75921e5cfe2d0924e177698f3b72804b2b2178`

完整836项source bindings、101inputs/3216rows/499计划快照/969static stages+FINAL已核验。Dynamic prefix仍用原mandatory674+fresh progress/confirmed精确union及支持案例完整prefix，不预填旧成绩。Exact hash inventory RAW：`9dfee9eeb85369f5a754f0074e04244fbf333d4d6f513c314c0c8620939bc6b6`。

独立只读回读run：[38761086285](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/38761086285)；9项合成拒绝检查PASS、真实Python Job/四raw captures/cleanup active0核验PASS，没有candidate import或formal qualification。

环境/dependencies见ENVIRONMENT_DEPENDENCY_LOCK.json，RAW：`4a68d805046b6d7b6946274cabd2ba37b69b44d82587e4865bed89d9d77f6877`。只允许20261004.326.1/20261012.333.1；Python3.11.9/Windows10.0.20348/AMD64/win22及全部依赖精确锁定，每个Job前后完整身份相同。未知第三镜像STOP；不主张每个案例已在两镜像分别执行。

## 范围和登记

- limited_scope_v2.json：RAW `09472bb1e20a1e3de197d85e865646440e1ffdfd5cf0c29a269609490c56ddfd`，完整注册软件fixture域，不代表整套真实运行/控制系统。
- SEM01 addendum v3：RAW `71a4f5e5843ca16dc9f654b71eb88747dd29113b7a2fe75a7bb660b1dbc2a78a`。PRE/Safety/真实模拟PLC事实不可回滚，POST不得赚第二样本；complete-only及四项登记软件失败cuts必须fresh测试。ARBITRARY_POST_EXCEPTION_ATOMICITY=NOT_PROVEN，T09=IMPLEMENTATION_HOLD。
- SEM02 five-case registry v1：RAW `291b8c2bb15869575f82c75f51628e60101cd6e9dd59673cd7864cef7491f7bd`。精确一条async重建trace＋四条invalid/rejected输入，strict P1 B/C仍INCOMPLETE；原Startup50、历史49/50与versioned compatibility分开，无伪造issue。
- PF06-C8-NORMAL-SUPPLEMENT-v1：RAW `76dd0a1138ce17247ae75afd0d078484a24a98c09e1d81184a0149b2d72da62f`。C8_normal row4/800ms、独立PRE/Safety/PLC/POSTcut、两原negative controls保留；original scope INCOMPLETE，补充需fresh执行，不改原C3-A。

上述四份登记bytes与v1相同；双镜像政策已单独获用户批准。这里保持独立签署栏，不代签，不把政策批准冒充新包冻结或执行许可。

真实硬件控制/production/Phase6未授权；full P history不可用，hardware CALIBRATION_REQUIRED；真实durable recovery、OS crash/power-loss原子性和未执行的跨镜像全案例等价性不在本包证明范围。不得用限定软件PASS掩盖这些缺口。

## 用户分别签署（全部待填写）

| 决定 | 用户批准/拒绝/保留意见 | 签署人及日期/时区 |
| --- | --- | --- |
| 1. 当前语义/范围登记及明确排除项 |  |  |
| 2. 上述确切包hash与EXECUTION_SOURCE_COMMIT的executable freeze |  |  |
| 3. 单独授权该身份从prepare开始full fresh formal C3-C |  |  |

EXECUTABLE_FREEZE_USER_APPROVED=NO；C3_C_FORMAL_EXECUTION_AUTHORIZED=NO；PRODUCTION_IMPLEMENTATION_AUTHORIZED=NO；HARDWARE_CONTROL_AUTHORIZED=NO；PHASE6=NO。

第2栏批准不隐含第3栏。正式执行不得借旧PASS；任一FAIL/INVALID保存并STOP，同execution不得修复重跑取PASS。最终绿色仍须独立回读行为证据及最后batch cleanup，才可作限定资格判定。