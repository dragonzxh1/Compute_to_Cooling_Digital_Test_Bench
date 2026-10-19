# 孟菲斯失败闭环与厂家性能验证 V1 — 最终开发交付

结论：软件开发执行完成，工程尚未批准，采购不得放行。
`MEMPHIS_ENGINEERING_NOT_APPROVED` / `NO_FEASIBLE_CANDIDATE` /
`OEM_NOT_VERIFIED` / `PROCUREMENT_RELEASE_STATUS=BLOCKED`。

这是90柜项目中一个18柜组的离线仿真与供应商规格准备，不是90柜整体
设计批准、Tier认证、生产/硬件控制、Phase6或新的正式C3-C资格。

## 先看这些文件

- [统一中文工程决策报告](../artifacts/memphis-failure-closure-v1-delivery/ENGINEERING_DECISION_ZH.md)：原5失败闭环决策表、16项答复、实际数字与未闭环边界。
- [事件增强交互报告](../artifacts/memphis-failure-closure-v1-delivery/engineering_report_event_complete.html)：在本地浏览器打开；两项A/B隔离/卡阀场景显示全部0.1秒物理步，其他曲线1秒抽样，所有判据均基于全步数据。
- [供应商RFI/FAT表](../artifacts/memphis-failure-closure-v1-delivery/supplier_RFI_FAT.csv)及[单体FAT/集成FAT/SAT拟议协议](../artifacts/memphis-failure-closure-v1-delivery/VENDOR_COMPONENT_FAT_INTEGRATED_FAT_SITE_SAT_ZH.md)：10类设备，厂家保证/签章空缺，未冒充已完成厂家试验。
- [完整交付hash清单](../artifacts/memphis-failure-closure-v1-delivery/package_manifest.json)、[源/输入/环境绑定](../artifacts/memphis-failure-closure-v1-delivery/source_input_environment_manifest.json)和[官方ZIP/原始文件/Job独立核验](../artifacts/memphis-failure-closure-v1-delivery/independent_file_verification.json)。原官方HTML/Markdown/JSON未改，增强输出有独立推导及hash记录。

本地完整交付：
`D:/Github/c2c-evidence-review/memphis-failure-closure-v1/run39180526734/delivery/`

## 执行身份与核验范围

- [实际运行39180526734](https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39180526734)
- execution source：`be3e9ea395ebd461683190d6cf3a0d5125973e13`
- source manifest RAW SHA256：`ba263422c76d02710e410c2071cc87b84d6faee82fd0d65e94cc4148adee7ce2`
- final package_manifest RAW SHA256：`6731f915c88e59ebdb78d04752a8e00e3a37b50209844908b8416089d8784b75`
- frozen M1 candidate SHA256：`70bba3a57f84847f0b486c0df3e4847a322933a1efb70eafb6b613bdbca348ce`；836保护来源和客户00/01最终原件再次hash核对未变。

127次动态仿真、340次独立罐放冷、40个受控阶段；20个官方ZIP及4425个
原始文件逐一验证hash。官方原始日志SHA256：
`58da1c24b185f971ac4f3cb0f632918e16eacde2bb987cecf51492d44a5a00e4`。
实际Python PID的外部Job证明、先证明再release、CPU25%、1024/2048MiB、
480s墙钟预算、固定环境和所有退出清理均核验，含FINAL退出后批处理。
本机未运行物理模型或native压力测试，仅作纯文件/流式JSON与浏览器检查。

原run39136524640的两组各17项、各5失败均从官方原始ZIP追溯。
10个失败工况新执行的峰温、90s峰温、负荷最低流量、冷返时间复现一致；
没有借用旧PASS。原13两组各1200帧的B命令均为0；本轮单独激发真实卡阀。
旧构建、失败与排队取消记录保留在专用分支历史及版本化说明，均未改原执行取PASS。
内部Build006是本任务开发构建号，不是新的C3-C版本。

## 直接影响工程决策的结果

1. 单纯预冷不是完整解。名义D/E峰温43.800°C、冷返34.2s，但17项包络D仍有3项、E仍有2项失败/不完整；没有全通过方案。
2. 无卡阀的A隔离切换，在35.1s出现物理步零流量；5Hz发布测量最低10.287m³/h漏过这一点。真实卡阀实际B命令1050帧未响应，最低178.968m³/h、峰温45.210°C。源侧恢复不等于负荷不断流。
3. 暖管预冷从48.29°C实际起算，2.75m³/90m³/h/100kW候选约844s达到登记温度条件；泵约0.769kW，不含风机/喷淋/冷服务用电。停泵失流即撤销Ready，不能拿仍冷的温度当许可。
4. 500/1000kW独立RC在600s均未恢复双罐可再次承担90s的资格；500kW的B罐起始44.188°C，不能用0.076K相对升温假装冷储备已恢复。
5. 15m³/85%冷液的0.005m³/s界面混合、5%短路例，20层升温0.783K而160层0.334K；不能选择细网格宣布通过。非零混合的连续物理意义/网格缩放仍未标定，NUMERICALLY_INCOMPLETE。

联合改进点另暴露10s阀与默认7s保护超时配置不匹配，39.7s锁存、最终
49.918°C。完整注册的12s超时联合变体实算43.800°C、334.763m³/h、冷返
44.2s；两组初始条件也不同，不能把其PASS移植给7s配置，更未自动放宽
客户90s/45°C/330m³/h或冻结M1要求。原始失败和参数全部保留。

## 仍需外部证据/正式工程决策

- 厂家共同工况性能面：湿源/单模块退出、低负荷预冷、泵Q-H/效率/NPSHr/启停、CDU污垢后能力、阀最大响应与反馈延迟。
- 罐的体积–高度/布水器/混合标定、85%冷量实证、回充真实末态再放冷及最坏回液FAT；阈值冷库存不等于90s动态资格。
- 业主确定单故障、维修、接管中再故障及共因设计基准；源W3不能消除共用负荷总管/单选择器缺口，不能非法并通A/B取PASS。
- 00/01约34m候选与R10整曲线≤18m冲突须分开选择；源静压、MAWP、水锤、PG物性与真实电耗仍未知，不能直接批准采购。

已形成可发厂家的RFI、分责任FAT/SAT方法及有界泵耗敏感性；没有虚构
OEM承诺、价格、年节能率、物理PLC签收或用户设计批准。冻结M1、历史
C3-C证据、原始fixture/contracts/profile/Safety、DSX/Twin/workbench和主
工作区用户资料均未修改。专用分支提交推送仅作开发/证据交付，未合并或发版。
