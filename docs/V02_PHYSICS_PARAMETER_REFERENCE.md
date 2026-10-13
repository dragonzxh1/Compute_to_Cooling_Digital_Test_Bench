# v0.2 物理、数值与保护参数参考

这是按现有源码核对的参数含义说明，不是校准证明、硬件安全配置或发布批准。
与 `M1_SOFTWARE_USER_GUIDE_DRAFT.md` 的tracking/控制/资源参数说明一起使用。
本轮没有运行任何Python模型或修改下面这些配置/源码。

## 1. 通用来源记录 ParameterRecord

源码：`v0_2/thermal/provenance.py`。物理量不是一个裸数字，应保留整个来源记录。

| 字段 | 意义 / 约束 |
| --- | --- |
| `name` | 参数名字；不能只凭名字猜温度或压力定义 |
| `value` | 有限数值，不接受bool冒充数值或NaN/Inf |
| `unit` | 精确单位字符串；`si()`目前检查单位，不是自动单位换算器 |
| `source_type` | OFFICIAL/DATASHEET/LITERATURE/ENGINEERING_ASSUMPTION/MEASURED/CALIBRATED来源类别 |
| `source_ref` | 可追溯出处或fixture身份，不能填“经验值”假装OEM数据 |
| `confidence` | 0～1的来源声明；不是该模型的概率准确率或PASS百分比 |
| `date` | ISO日期；参数来源的记录日期 |
| `valid_range` | 本参数value的声明范围，与整个模型的适用域不同 |
| `calibration_status` | UNVALIDATED/CALIBRATION_REQUIRED/CALIBRATED/VALIDATED；不得自动提升 |

`fixture_parameter()`生成ENGINEERING_ASSUMPTION、confidence=0、UNVALIDATED记录。这样做能重现数学测试，不能证明GB300、CDU或VFD硬件参数。

## 2. 热容、温度与热源

### ThermalNodeState / ConstantCapacity

源码：`thermal/nodes.py`。当前只实现恒定热容，`ConstantCapacity.capacitance`单位J/K。
节点储能满足 `energy_j = thermal_capacitance × (temperature_k-reference_temperature_k)`。

| 字段 | 意义 |
| --- | --- |
| `node_id` / `entity_id` | 热节点和所属设备身份；不同实体不能共享一个储能节点假装两份容量 |
| `node_type` | GPU_DIE/GPU_PACKAGE/HBM/VRM_BOARD/CPU_DIE/CPU_PACKAGE/COLD_PLATE/LOCAL_COOLANT/RACK_AIR |
| `temperature_k` | 节点代表温度K；die/package/plate/bulk含义不能混用 |
| `energy_j` | 相对reference温度的存储能量J；不是累计IT耗电 |
| `thermal_capacitance` | 恒定C，J/K，必须>0 |
| `reference_temperature_k` | 储能零点，不是环境温度，也不是控制设定值 |
| `storage_owner_id` | 这一份物理储能的唯一owner |
| `valid_temperature_range` | 数值模型温度域；越界MODEL_OUT_OF_RANGE，不把温度强行裁回范围 |
| `provenance` / `calibration_status` | 来源与热容记录校准状态一致，不能单独给节点贴CALIBRATED标签 |
| `mass_kg` / `specific_heat` | LOCAL_COOLANT必需，kg与J/(kg*K)，满足C=mass×cp |
| `coolant` | 冷却液身份；LOCAL_COOLANT不能缺失或与流量对象不符 |
| `adiabatic` | 节点绝热声明；不是把未解释的漏能量置零 |

`ThermalState.nodes/time_ns`为纯热模型当前节点组与时间；`ThermalTopology.initial_state/interfaces/device_cvs`声明初态、唯一热交换接口，以及设备控制体包含哪些节点。`device_cvs`用于审计，不额外增加一份储能。

### PowerLeaf / PowerSourceMap

源码：`thermal/source_mapping.py`。

| 字段 | 意义 |
| --- | --- |
| `source_id` | 一个独立电功率leaf的身份；每拍只能向热模型映射一次 |
| `component_kind` | 对应热节点类型；BOARD_POWER必须先分配，不能直接注入die |
| `power` | 电功率W的ParameterRecord，非负 |
| `component_ids` | 该功率包含哪些物理部件；不能与另一个leaf重叠计功率 |
| `included_in` | 父功率聚合关系；不能同时把父和其子leaf作为独立热源 |
| `value_origin` | MEASURED_DIRECT/ALLOCATED_FROM_PARENT/ENGINEERING_ASSUMPTION/CALIBRATED_ESTIMATE |
| `sample_time_ns` | 该功率记录的时间，不允许未来采样冒充当前测量 |
| `PowerSourceMap.assignments` | `(source_id, thermal_node_id)`不可变映射，必须完整、一一接收、类型相符 |

功率不是温度。输入W在区间内保持时，热输入J=功率×区间秒数；热模型必须通过C/R/冷却路径计算温度，不能直接把GPU功率当结温。

## 3. 热阻接口与冷板

### ThermalInterface

源码：`thermal/interfaces.py`。

| 字段 | 意义 |
| --- | --- |
| `interface_id` | 唯一热交换接口身份 |
| `hot_node_id` | 热端节点；“hot”是符号方向，热量实际可反向 |
| `cold_node_id` / `external_boundary_id` | 二选一：内部冷端或无存储的外部边界，不能两者都有/都无 |
| `resistance_model` | 正热阻ParameterRecord(K/W)，或GenericColdplate；导热系数是1/R(W/K) |
| `included_layer_ids` | 此接口已包含哪些真实热阻层，防止TIM/冷板导热等重复计入 |
| `owner_id` | 唯一通量owner；同一热交换不能在两处各算一次 |
| `kind` | CONDUCTIVE_RESISTANCE/CONVECTIVE_RESISTANCE/COLDPLATE_FLOW_DEPENDENT/PRESCRIBED_BOUNDARY |
| `provenance` / `validity` | 来源与有效性；invalid本构关系不能偷偷当正常接口 |
| `boundary_medium` | 外部AIR/LIQUID/OTHER分类；内部接口应为None |

内部接口只产生一份热流，在相邻节点等量异号记账。外部边界的热量单独记出入，不会给边界创建隐藏热容。

### ColdplateDefinition / GenericColdplate / FlowInput

源码：`thermal/coldplate.py`。GenericColdplate的已实现关系：

`h = h_ref × (abs(mass_flow)/m_ref)^exponent`；`R = conduction_r + 1/(h×area)`；`Q=(hot-cold)/R`。

| 字段 | 意义与单位 |
| --- | --- |
| `definition` | 冷板端点及层包含声明，下表详细解释 |
| `h_ref` | 参考流量处对流换热系数，W/(m2*K)，>0 |
| `m_ref` | 参考质量流量kg/s，>0 |
| `exponent` | 流量对h的指数，fraction，0<指数≤1；不是泵转速指数 |
| `conduction_r` | 板内导热部分，K/W，>0，不包含上游die/package/TIM |
| `area` | 对流有效面积m2，>0；不是整机外形面积 |
| `flow_range` | 强制流动模型的有效质量流量范围kg/s，低端>0 |
| `temperature_range` | 热端与冷端都必须处于该K范围 |
| `heat_load_range` | 已计算接口热流绝对值的W范围，不是GPU额定电功率 |
| `coolant` / `provenance` | 液体身份和系数来源 |
| `zero_policy` | MODEL_INVALID（默认）或ZERO_FLOW_VALID_MODEL；零流不能靠加epsilon洗成正常 |
| `no_flow_resistance` | 只有登记零流有效模型时可用，有限K/W且≥conduction_r；默认None |
| `bidirectional` | 是否允许负流；开启声明也不能绕过其他拓扑/输运模块的反向限制 |
| `FlowInput.mass_flow` / `FlowInput.coolant` | 测试施加的质量流量ParameterRecord(kg/s)与同一液体身份 |

ColdplateDefinition字段：`thermal_hot_endpoint_id/thermal_cold_endpoint_id`是具体端点；`hot_side_temperature_definition/cold_side_temperature_definition`明确温度含义；`rth_definition`说明R包含哪段；`included_layers/excluded_layers`不可重叠。`manufacturer_rth_definition/manufacturer_measurement_hot_endpoint/manufacturer_measurement_cold_endpoint`必须与导入定义一致，默认NOT_APPLICABLE。

Generic模型只允许代表板固体到local well-mixed bulk coolant的定义，包含板内导热和板-液对流两层。`ManufacturerColdplateSchema.definition/provenance`当前只做进口schema校验，**没有实现厂商曲线计算器**，不能把schema通过称为性能仿真通过。

## 4. 液体焓、储液与输运

### ConstantCpFluid / CoolantVolumeState

源码：`fluids/properties.py`和`coolant/volume.py`。

| 字段 | 意义 |
| --- | --- |
| `ConstantCpFluid.fluid_id` | 液体/回路身份，一次侧与二次侧不能假装同一个混合体 |
| `density` | 密度kg/m3，>0，用于Q(m3/s)与质量流量的换算 |
| `specific_heat` | 恒定cp，J/(kg*K)，>0；目前不实现温变cp |
| `reference_temperature` | 比焓零点K；h=cp×(T−Tref)，不是保护温度 |
| `valid_temperature_k` / `provenance` | 流体模型适用K范围与来源 |
| `CoolantVolumeState.volume_id` | 有限储液体身份 |
| `mass_kg` | 固定存储液体质量kg，>0；不是流量 |
| `specific_enthalpy_j_kg` | 比焓J/kg，必须与temperature_k和fluid关系一致 |
| `temperature_k` | 该well-mixed有限体积的代表K温度 |
| `pressure_pa` | 绝对压力Pa，非负；不能拿表压/压差直接冒充 |
| `coolant_ref` / `fluid` | 必须指向相同fluid_id的流体模型 |
| `storage_owner_id` / `provenance` | 这一份液体储能唯一owner与来源 |

液体能量是mass×h。停流时residence time返回None，而不是假设立即传递；有流时停留时间=mass/abs(mass_flow)。

### AdvectiveLink / FluidConnection

源码：`coolant/advection.py`和`plant/loop.py`。

`AdvectiveLink.link_id/from_id/to_id`定义单份输运通量和端点；`mass_flow_kg_s`是有符号质量流量；`owner_id`唯一；`reverse_supported`默认False。反向合法时donor/receiver换向，不能把负流直接当正流却继续用旧热端。

`solve_implicit(volumes, links, dt_s, boundary_enthalpy, heat_w)`：`volumes`是已有储液，`links`是输运连接，`dt_s`必须>0，`boundary_enthalpy`是无存储外部端口的J/kg映射，`heat_w`是施加到已有体积的W映射。端口不能与储液ID重复，每个液体体积流入流出质量守恒。

`FluidConnection.link_id/from_volume_id/to_volume_id/branch_index`将physical loop的连接绑定到水力支路；branch_index=None表示公共路径，不是“未知但可随便选支路”。有限体积upwind输运与固定FIFO延迟不能同时拥有同一条路径。

## 5. 水力网络与泵功耗

### PumpCurve

源码：`hydraulics/pump.py`。当前曲线：`head = shutoff_head_pa×actual_speed² − curve_k×flow_m3_s²`。

| 字段 | 意义 |
| --- | --- |
| `shutoff_head_pa` | 归一化speed=1、零流处标称扬程Pa，>0 |
| `curve_k` | 扬程随体积流量平方下降的系数，Pa/(m3/s)^2，≥0 |
| `speed_range` | 曲线有效归一化actual speed域；不等于tracking命令上下界一定相同 |
| `flow_range_m3_s` | 曲线有效体积流量域m3/s，不能直接填kg/s |
| `provenance` | 曲线来源；这里不是厂商完整多点效率map |

超域或负扬程停止MODEL_INVALID/OUT_OF_RANGE；不裁剪曲线伪造满足需求的流量。

### HydraulicEdge / PressureNode / HydraulicGraph

源码：`hydraulics/graph.py`。被动压降为 `coefficient×Q×abs(Q)`。

| 字段 | 意义 |
| --- | --- |
| `PressureNode.node_id/loop_id` | 压力接点身份与单独回路身份 |
| `HydraulicEdge.edge_id/from_node/to_node` | 水力阻力段及方向，不能自接或重复edge |
| `kind` | PIPE/MANIFOLD_CONNECTION/GENERIC_RESISTANCE/COLDPLATE_RESISTANCE/VALVE；当前都以登记K形式计算 |
| `coefficient` | 正阻力系数，Pa/(m3/s)^2；增大它通常降低该路径流量，不直接是阀开度% |
| `valid_q_m3_s` | 被动段有效体积流量绝对值域 |
| `receiver_id/liquid_fraction` | 阻力耗散接收体与分到液体的比例0～1，防重复热量记账 |
| `provenance/reverse_supported` | 来源与负流支持声明，默认不支持 |
| `HydraulicGraph.nodes` | 所有压力接点；必须同一loop，无孤立节点 |
| `return_node/pump_outlet_node/supply_manifold/return_manifold` | 回流、泵出口、供回总管接点身份 |
| `supply_series/branches/return_series` | 供水串联、并联支路组、回水串联路径，必须端点连续 |
| `pump_edge_id` | 唯一泵edge身份，不与普通压力节点混同 |

### PumpDrive

| 字段 | 意义 |
| --- | --- |
| `vfd_efficiency/motor_efficiency/pump_efficiency` | VFD、电机、泵级效率，fraction，0<η≤1；分别计损耗，不把液压功当全部电功 |
| `vfd_liquid_fraction/motor_liquid_fraction/internal_liquid_fraction` | 每级损耗进入液体的比例0～1，余量进环境 |
| `liquid_receiver_id` | 损耗热进入哪个储液体 |
| `provenance` | 效率/热分配来源 |
| `standby_electrical_w` | 液压输出为零时登记的待机W，不能假设泵无功耗 |

液压功率=head(Pa)×体积流量(m3/s)，单位W。当前仅motoring；泵液压功在被动阻力处耗散，不再次在泵处当液体热加一遍。VFD/电机/内部损耗按上述热去向计入。

## 6. CDU 换热器 / FWS

源码：`cdu/heat_exchanger.py`。当前ε-NTU、恒定cp、两侧独立回路，不是厂商CDU完整控制器。

| 字段 | 意义 |
| --- | --- |
| `ua` | 总体换热导度UA，W/K，>0；不是总功率W |
| `arrangement` | COUNTERFLOW逆流或PARALLEL并流；影响effectiveness公式 |
| `secondary_fluid/primary_fluid` | 二次侧冷却回路与一次侧FWS流体模型，fluid_id必须不同 |
| `valid_secondary_flow/valid_primary_flow` | 两侧有效**质量**流量域kg/s；与水力体积流量域不同 |
| `rated_capacity_w` | 可选额定绝对换热W上限；None表示没声明cap，不表示已证明无限容量 |
| `provenance` | UA/布置/容量来源 |

`evaluate()`的secondary_flow、primary_flow单位kg/s；secondary_inlet_k、primary_inlet_k单位K。一侧停流返回零换热；超rated_capacity是MODEL_OUT_OF_RANGE，不把热量裁到额定值继续PASS。热量方向来自两侧入口温差，允许合法反向换热而不是负热量一律归零。

## 7. PhysicalPlant / PlantInput / 场景事件

源码：`plant/loop.py`。

| 字段 | 意义 |
| --- | --- |
| `PlantState.solids/volumes/time_ns` | 固体状态、储液状态及同一模型时刻；各物理inventory唯一 |
| `PhysicalPlant.initial_state/interfaces/connections` | 初态、热交换接口、实际有限体积输运连接 |
| `coldplate_branches` | 冷板interface到水力branch_index的唯一映射 |
| `hydraulic_graph/pump_curve/pump_drive/heat_exchanger/source_map` | 上述已定义的模型对象，不是一个新的重复参数副本 |
| `cdu_volume_id` | CDU二次侧有限储液体的ID，必须存在 |
| `volume_pressure_nodes` | 每个储液体对应哪个压力接点，必须完整无重复 |
| `provenance/pressure_reference_pa` | 系统来源与绝对压力参考Pa，>0；后者不是DP目标 |
| `legacy_fifo_enabled` | Physical loop中禁止与advection同时为True |
| `pump_hydraulic_heat_at_pump` | 有被动耗散receivers时禁止True，避免液压热双计 |
| `PlantInput.speed_actual` | 当前物理actual speed；仅plant/measurement消费，控制器不能直接读它 |
| `primary_mass_flow` | FWS一次侧质量流量ParameterRecord，kg/s |
| `fws_inlet_temperature/ambient_temperature` | FWS入口/环境边界K；不是控制器可偷读的未来schedule |
| `electrical_leaves` | 当前interval的功率leaf组，由source_map一次映射 |

`THERMAL_VALIDATION_BATH`与`PHYSICAL_COOLANT_LOOP`互斥：前者是验证热模型用的外部恒温液体边界，后者是有储液和输运的实际数值拓扑。同一冷却路径不能同时接bath/FIFO/advection。

纯热`Fixture.topology/source_map/sources/boundaries/flows`打包上述热拓扑、源映射、功率、边界温度和局部流量。`BoundaryEvent.time_ns/sources/boundaries/flows`在特定模型时刻替换区间输入。physical `PlantEvent.time_ns/controls`替换完整PlantInput。事件是scenario injector拥有的强迫，不是FF/PID可预读的未来数据。

feedback `ControlClocks.physics_ns/outer_ns/plc_ns/actuator_ns/safety_ns`分别定义五种调度周期，均为整数ns且至少1000。`Disturbance.time_ns`是事件时刻；`power_each_w`是每个登记设备leaf的W；`fws_inlet_k`是FWS入口K；`primary_flow_kg_s`是一次侧kg/s；`branch_zero_k_multiplier`改变示例branch0水力阻力；`sensor_failures`是失效通道名；`pump_stuck`是故障注入。None意为该事件不改此项，不能把它当0。

## 8. 数值方法与验收阈值

源码：`thermal/integrator.py`、`thermal/harness.py`、`plant/phase4_harness.py`。

| 参数/设置 | 意义 |
| --- | --- |
| `duration_ns` | 模型实验持续时间，正整数ns；不是进程timeout |
| `dt_ns` / `dt_s` | 积分区间ns/输运区间s；事件会切分步长，不能跨事件预用新值 |
| `Method.BACKWARD_EULER` | 默认恒定C、区间保持导度下的保守后向Euler |
| `EXPLICIT_EULER` | 带正性/稳定性检查的debug参考，不是失败时自动fallback |
| `EXACT_LINEAR` | 同一线性RC模型的精确参考，不声称通用非线性精确解 |
| `MAX_ITERATIONS=25` | 预留非线性上限；当前实际是direct linear solve，不是已实现25次非线性求解 |
| `MAX_STEP_HALVINGS=10` | 允许重试分半最多10层，不是quietly忽略失败 |
| `MIN_DT_NS=1000` | 最小1µs模型步；失败返回原state和空committed ledger |
| `reference_limit_k` | 热harness默认400K的数值headroom参考，不是GB300硬保护温度 |

能量/质量误差阈值是数值守恒的门槛，不是传感器容差。不能靠扩大它们掩盖重复热源或漏热。累计signed residual与累计absolute residual必须分别看，正负误差互相抵消并不证明模型正确。mesh比较要同输入/事件/方法/持续时间，不能把0.2s与0.05s强制比较同sample index。

## 9. SafetyPolicy 保护参数

源码：`safety/supervisor.py`。这是现有物理反馈配置字段说明，**不宣称production实现已经满足全部15/15A/new-M1 mapping**；后者需要独立验收，不能改代码来追求文档所写PASS。

| 字段 | 意义 |
| --- | --- |
| `control_target_k` | 正常控制目标K；必须低于derate_k，不作为hard触发 |
| `operating_limit_k` | 工作/headroom性能参考；不是默认保护门槛 |
| `derate_k/hard_k` | 降额/硬保护触发K，要求control_target<derate<hard；需来源和同温度定义 |
| `derate_clear_k/hard_clear_k` | 两层独立恢复K门槛，分别低于自己的触发值 |
| `minimum_flow_kg_s` | 保护用最小质量流量kg/s，不能使用hiddenACTUAL |
| `maximum_dp_pa` | 物理保护最大DP；不等于正常setpoint上限 |
| `fallback_dp_pa` | 已登记的fallback目标，不保证所有故障都适合它 |
| `minimum_dp_pa/maximum_target_dp_pa` | 正常/受限目标包络边界，minimum≤fallback≤maximum_target |
| `maximum_target_rate_pa_s` | 被接受DP目标每秒最大变化Pa/s；不是执行器归一化ramp |
| `fault_speed` | 现有generic策略的故障速度fraction；真实fault/action table不得猜总是最大泵速 |
| `dwell_ns` | 已配置状态驻留时间，默认2s；严重升级不能因dwell等待 |
| `recovery_samples` | 恢复所需distinct有效samples，默认5；重复旧sample不能赚次数 |
| `source` | 数值假设/测量/OEM依据声明，不改变保护语义 |

SafetyEnvelope的`minimum_dp_pa/maximum_dp_pa/minimum_speed_fraction/maximum_speed_fraction/fallback_dp_pa/shutdown_required`是限制，不是Safety直接签发泵command。`envelope_id/created_ns/valid_until_ns/accepted_target_id/source_measurement_ids/reason_codes/request_id/producer_module`保留因果、有效期和所有原因；PLC才创建最终ActuatorCommand。测量恢复或POST变STEADY都不能清已confirmed的FAULT latch。

## 10. 配置与结果不要混淆

`PumpEnergy`的electrical/hydraulic/loss W、`HXExchange`的outlet温度/effectiveness/heat W、`ColdplateExchange`的热流/R、`PlantStep`的status/ledger、`ControlledRow`的command/actual/measured/IDs是**计算结果或证据**，不是可以倒改来让模型PASS的参数。

`ControlIntent`中的`created_ns/available_ns/expires_ns`管输入可见性和有效期；`requested_dp_pa/fb_component_pa/ff_component_pa`分别是请求目标、FB修正和FF修正，现有Phase5是feedback-only。`intent_id/source/validity/reason`是来源；`AcceptedTarget.accepted_target_id/created_ns/requested_dp_pa/producer_module/fb_intent_id/reason/source_ids`是监督器接受记录，不是现场PLC已执行的证明。

质量/数值越界会CONFIG_INVALID、MODEL_INVALID或MODEL_OUT_OF_RANGE；不能用“加一个小值”“换一个单位名”“把输出夹住”伪装恢复。修改冻结域的参数、保护门槛或计时规则是新校准/语义工作，不在当前POST缺陷修复中。
