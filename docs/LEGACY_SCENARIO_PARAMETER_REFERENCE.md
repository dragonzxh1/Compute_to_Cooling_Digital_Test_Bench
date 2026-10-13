# 旧 v0.1 YAML 与报告参数说明

适用：configs/scenarios/workload_step.yaml、src/c2c/simulation/engine.py、validation.py、runner.py和对应模型源码。仅静态源码说明；本轮没有重新运行旧benchmark。此入口与M1 source SDK不同，SDK不包含src/c2c的报告应用。

旧应用CLI：c2c-dtb [config] --output-root results --locale zh-CN。config是YAML路径（省略时寻找安装目录或源码中的workload_step.yaml），output-root是新运行报告的父目录，locale可选en/zh-CN。默认每次产生独立时间戳目录，包含config.yaml、metadata.json、timeseries.csv、summary.json、comparison.png、response_timeline.png、response_events.json和report.html。不要在已知硬挂本机执行该Python命令。

以下路径均指YAML，值是数值假设，不是NVIDIA/CDU硬件默认值。value/unit/source_type/source/date/confidence/notes一起保存；来源记录经ParameterRecord校验，再提取value用于模型。不要用一张报告把ASSUMED变成CALIBRATED。

## 场景与负载

| 参数 | 意义 / 单位 / 限制 |
| --- | --- |
| name / description | 场景身份与文字说明；name进入输出目录名 |
| seed | 运行元数据中的seed；当前合成step trace确定性生成，不等于本轮使用随机噪声 |
| time.dt_s | 仿真离散步长s，>0；需满足RC稳定性约束，不是传感器周期或墙钟预算 |
| time.duration_s | 仿真总时长s，>0；不是GitHub任务超时 |
| workload.type | 场景负载类型描述；当前SyntheticWorkloadSource按phases执行 |
| workload.phases[].start_s | 阶段起点s；首项0，严格递增且不超过duration；基准窗口必须有足够采样 |
| workload.phases[].utilization_pct | GPU利用率0..100%，不是转速、散热捕获率或功率百分比的共同单位 |
| workload.phases[].workload_type | telemetry中的负载标签；不是自动选择真实GPU任务 |

## 算力、热量与冷却液

| 参数 | 意义 |
| --- | --- |
| compute.gpu_count | 机柜GPU数量，正整数；示例72不是设备探测结果 |
| compute.gpu_idle_power_w / gpu_max_power_w | 每GPU空闲/满负载功率W；idle<=max |
| compute.gpu_power_limit_w | 每GPU模型功率上限W，必须在idle与max之间；不下发真实GPU限功率 |
| compute.cpu_power_w / other_power_w | 全机柜CPU/其他设备总功率W，非负，不能再乘GPU数量 |
| heat_capture.alpha_gpu / alpha_cpu / alpha_other | 各类电功率进入液冷路径的比例0..1；剩余热量计入空气侧，需量热校准 |
| fluid.name | 冷却液身份；当前恒物性模型，不自动下载物性表 |
| fluid.density_kg_m3 | 密度kg/m³，>0；质量流量=体积流量×密度 |
| fluid.cp_j_kgk | 定压比热J/(kg·K)，>0；传热与温差关系Q=质量流量×cp×ΔT |

## 热网络、水力与CDU

| 参数 | 意义 |
| --- | --- |
| thermal.ambient_c | 旧配置保留的环境温度°C；当前run_case由steady_initial_state初始化，不以该值计算RC对空气散热 |
| thermal.c_die_j_k / c_package_j_k / c_cold_plate_j_k / c_coolant_j_k | 聚合die/package/冷板/冷却液的热容J/K，>0；值越大温度变化越慢，不是热阻 |
| thermal.r_die_package_k_w / r_package_plate_k_w / r_plate_coolant_k_w | 相邻聚合节点热阻K/W，>0；不是单GPU热阻；旧冷板热阻固定，不自动随流量变化 |
| thermal.transport_delay_s | 固定管道输运延迟s，>=0；不是V0.2有限容积焓输运模型 |
| thermal.throttle_temp_c | 报告GPU温度/throttle判据°C；示例90不是OEM热保护温度，不实际节流GPU |
| hydraulics.system_k_pa_s2_m6 | 系统压降系数Pa/(m³/s)²，>=0 |
| hydraulics.pump_k_pa_s2_m6 | 二次泵曲线下降系数同单位，>=0；两种阻力系数之和必须>0 |
| hydraulics.pump_shutoff_dp_pa | 参考转速关死压差Pa，>0；与目标kPa要换算，不等于现场额定曲线 |
| hydraulics.pump_efficiency | 恒定泵效率0<η<=1，用于功率估算；不是variable-speed效率图 |
| cdu.ua_clean_w_k | 洁净换热UA，W/K，>0；不是换热功率W |
| cdu.fouling_factor | UA乘数0..1；1表示数值洁净基线，越小换热越弱 |
| cdu.primary_inlet_temp_c | 设施水入口°C，边界条件 |
| cdu.primary_max_flow_m3_s | 阀100%时设施侧最大体积流量m³/s，>=0；当前阀位线性缩放 |

## PLC、本地PID与上层建议

| 参数 | 意义 |
| --- | --- |
| controls.dp_target_kpa / supply_temp_setpoint_c | 本地回退目标压差kPa/供液温度°C |
| controls.dp_min_kpa / dp_max_kpa | 允许的目标DP范围kPa，min<=max；不是证明真实压力始终在范围内 |
| controls.supply_temp_min_c / supply_temp_max_c | 被接受温度目标范围°C，min<=max |
| controls.pump_speed_min_pct / pump_speed_max_pct | 泵命令范围0..100%，与M1的0..1归一化速度不同 |
| controls.valve_min_pct / valve_max_pct | 阀位命令范围0..100%，min<=max |
| controls.pump_ramp_pct_s / valve_ramp_pct_s | 每秒允许泵/阀命令变化的百分点，>=0 |
| controls.temp_setpoint_ramp_k_s | 接受目标与回退目标的平滑速率K/s，>0；不是阀位速率 |
| controls.intent_timeout_s | 上层intent有效年龄s，>=0；未来intent/过期intent不接受 |
| controls.dp_deadband_kpa / temp_deadband_k | 目标附近误差死区kPa/K，>=0；不是fault threshold |
| controls.dp_pid.kp / ki / kd | 压差PID比例、积分、微分增益：%/kPa、%/(kPa·s)、%·s/kPa，非负；kd=0禁用微分 |
| controls.temp_pid.kp / ki / kd | 温度PID增益：%/K、%/(K·s)、%·s/K，非负；正温差增大阀位 |
| lci.update_interval_s | ShadowLCI建议更新间隔s，>0，不改变PLC/模型dt |
| lci.target_delta_t_k | 用于Q/(cp·ΔT)估算所需流量的目标液体温升K，>0 |
| lci.min_supply_setpoint_c / max_supply_setpoint_c | 上层温度建议上下界°C；PLC仍独立限幅 |
| lci.min_dp_setpoint_kpa / max_dp_setpoint_kpa | 上层DP建议上下界kPa；不是直接签发泵命令 |

旧ShadowLCI根据当前模型液冷热负荷估计流量与DP，不是训练出来的GPU预测器。供液温度建议使用源码中的110000W归一化负载尺度、30.5°C截距和4.5K负载修正（最终限幅），这些是固定研究假设，不是可配置硬件参数。本任务不改该旧算法，也不等于启动V0.2 Phase6。

## 报告阈值与数值怎么看

| 参数 | 意义 |
| --- | --- |
| reporting.facility_cop | 设施估算COP，>0；设施冷却电功率=排热功率/COP，只用于报告假设 |
| reporting.limits.max_supply_deviation_k | 最大供液温度偏离目标K，>0，报告验收阈值 |
| reporting.limits.max_steady_heat_balance_error_pct | 稳态热平衡相对误差上限%，>0；不是要求瞬态储能阶段输入=输出 |
| reporting.limits.max_valve_oscillation_index_pct | 高负载窗口阀位步差的标准差上限，%/步，>0；不是温度标准差，也不直接约束泵 |

报告阈值和PLC保护不是一回事。实际值超过阈值时该项应FAIL，不能为了漂亮图表扩大阈值。1.384e-06表示0.000001384：接近无振荡，不是大于1；展示小于0.0001不会把原数据改成0。INCOMPLETE、INVALID、FAIL和正常采样等待要分开。

功率积分按区间左端保持值计算kWh。GPU温度、液体温度、压力、功率、泵速与阀位是不同信号。response_timeline中功率/intent/泵/阀/温度/压力的出现顺序是这个简化模型的时间证据，不是现场网络/设备延迟保证。

该参考按完整默认workload_step.yaml字段和源码读取路径说明，不宣称未来第三方YAML扩展自动有对应行为。源码SDK、旧HTML应用与V0.2物理模型的验证范围分别记录，不能互借PASS。
