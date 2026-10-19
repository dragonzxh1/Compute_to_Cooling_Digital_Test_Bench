# Memphis hydraulic continuity and reserve recovery V1

本任务由用户授权新的专用分支 `codex/memphis-hydraulic-continuity-v1` 提交、推送和有界GitHub开发测试。不合并、不发版、不运行正式C3-C或真实设备，不扩展MCU硬件，不更改冻结M1或历史交付。

基线身份：Failure Closure run39180526734，execution `be3e9ea395ebd461683190d6cf3a0d5125973e13`，delivery `e8fd76847f5daa57ae266b772375dca404af3b12`。00/01原件哈希不变。

首先修正建模边界，不能先宣布客户架构有缺陷：00/01要求源侧换路时负荷泵继续供流；允许必要的一对CDU和负荷泵短时重叠；禁止A/B一次环网并通、不允许三组同时重叠。旧单选择器break-before-make结果作为旧模型失败证据保留，不冒称完整00/01实装拓扑的失败证明。

范围：原离散轨迹的断流区间/亏缺体积独立核算；忠实源侧切换与分段回充；与明确新增硬件的候选进行联合热水力比较；真实泵/CDU成对接管和未激发负控分别注册；压力瞬态与NPSH/静压未标定边界单列，禁止以准稳态交点或更细dt冒称水锤资格。

所有物理/布尔测试只在外部验证实际Python PID的受控GitHub Job中运行，CPU25%、1024/2048MiB、每阶段480s及冻结源前后核验维持。普通本地文件读取、hash、纯证据解码不执行模型。

工程状态保持 `MEMPHIS_ENGINEERING_NOT_APPROVED`。任何硬限或保护源漂移必须停止受影响操作。
