from __future__ import annotations

SUPPORTED_LOCALES = ("en", "zh-CN")

_TRANSLATIONS = {
    "en": {
        "timeline.title": "Control response timeline — first load step",
        "timeline.time": "Time relative to load step (s)",
        "timeline.axis_power": "GPU power (kW)",
        "timeline.axis_temp_target": "Supply target (°C)",
        "timeline.axis_dp_target": "Pressure target (kPa)",
        "timeline.axis_pump": "Pump speed (%)",
        "timeline.axis_valve": "Valve position (%)",
        "timeline.axis_temperature": "PLC temperature input\nchange from baseline (K)",
        "timeline.axis_pressure": "PLC pressure input\nchange from baseline (kPa)",
        "timeline.accepted": "Accepted final target",
        "timeline.actual": "Ramped control setpoint",
        "timeline.power": "GPU power change ≥ 1 kW",
        "timeline.intent": "First refreshed post-step LCI intent (shadow in feedback case)",
        "timeline.pump": "Pump movement ≥ 2 percentage points",
        "timeline.valve": "Valve movement ≥ 2 percentage points",
        "timeline.temperature": "PLC temperature input departure ≥ 0.1 K",
        "timeline.pressure": "PLC pressure input departure ≥ 0.2 kPa",
        "timeline.delay": "Delay from load step (s)",
        "timeline.none": "Not reached in high-load window",
        "timeline.explanation": (
            "GPU power → estimated liquid heat → supervisory targets → PLC pump/valve commands. "
            "Left: feedback; right: power feedforward. The chart zooms to 30 s before and "
            "180 s after the first step; the table covers the entire first high-load phase. "
            "Purple lines mark first absolute departures from the preceding 60 s mean "
            "(or available pre-step samples); thresholds are listed below. LCI refresh is "
            "not target acceptance in the shadow case. Sensor traces are inputs read by "
            "the PLC before that row's commands, not the post-command plant outputs."
        ),
        "timeline.limits": (
            "These are simulated threshold crossings, not sensor detection times or causal "
            "proof. Feedforward itself changes temperature and pressure. The model has no "
            "sensor acquisition/communication delay; its static hydraulic resistance does "
            "not change with GPU heat. Power feedforward reacts to current load, does not "
            "predict future work, and does not use junction temperature as a control input. "
            "Temperature/pressure feedback remains active."
        ),
        "report.title": "C2C-DTB V0.1 benchmark",
        "report.page_title": "C2C-DTB report",
        "report.explanation": (
            "Both cases use identical feedback control before {step_s:g} s. Feedforward "
            "is enabled at the load step. Setpoint and valve response delays are measured "
            "separately; valve delay uses the same 2 percentage-point threshold in both cases."
            " The supply-deviation check uses the actual ramped setpoint; error to the "
            "final accepted target is reported separately and is not covered by that PASS."
        ),
        "report.kpis": "KPIs",
        "report.threshold_checks": "Threshold checks",
        "report.case": "Case",
        "report.metric": "Metric",
        "report.value": "Value",
        "report.limit": "Limit",
        "report.status": "Status",
        "report.pass": "PASS",
        "report.fail": "FAIL",
        "report.invalid": "INVALID DATA",
        "report.overall": "Overall status",
        "report.plot_alt": "Benchmark comparison plots",
        "metric.validation_errors": "Invalid input columns or windows",
        "metric.startup_supply_deviation_k": "Startup supply deviation (K)",
        "metric.post_step_supply_deviation_k": "Post-step supply deviation (K)",
        "metric.setpoint_response_delay_s": "Setpoint response delay (s)",
        "report.interpretation_limits": "Interpretation limits",
        "report.limits_text": (
            "This demonstrates model behavior and timing, not verified GB300 or CDU "
            "performance. Replace ASSUMED parameters and validate against FAT/SAT data "
            "before operational use. GPU-labelled temperatures represent an aggregate "
            "equivalent hotspot including CPU/other liquid heat. Startup is not joint "
            "plant equilibrium. The steady heat-balance check does not validate transient "
            "pipe energy storage."
        ),
        "claims.generic": (
            "Generic assumed equipment; comparative engineering result, not OEM prediction."
        ),
        "case.feedback_only": "Feedback only",
        "case.guarded_feedforward": "Guarded feedforward",
        "plot.gpu_power_kw": "GPU power (kW)",
        "plot.gpu_temperature_c": "Equivalent hotspot temperature (°C)",
        "plot.secondary_supply_temp_c": "Secondary supply (°C)",
        "plot.secondary_return_temp_c": "Secondary return (°C)",
        "plot.secondary_flow_m3h": "Secondary flow (m³/h)",
        "plot.pump_power_kw": "Pump power (kW)",
        "plot.time": "Simulation time (s)",
        "plot.ramped_target": "Feedforward ramped setpoint",
        "plot.final_target": "Feedforward final target",
        "plot.title": "C2C-DTB V0.1: feedback-only vs guarded GPU-power feedforward",
        "check.gpu_temperature": "Peak equivalent hotspot temperature",
        "check.supply_deviation": "Maximum tracking error to ramped setpoint",
        "check.heat_balance": "Steady-state heat-balance error",
        "check.valve_oscillation": "Valve command step-change standard deviation",
        "check.pump_speed_min": "Minimum pump speed",
        "check.pump_speed_max": "Maximum pump speed",
        "check.valve_position_min": "Minimum valve position",
        "check.valve_position_max": "Maximum valve position",
        "check.accepted_temp_min": "Minimum accepted supply-temperature setpoint",
        "check.accepted_temp_max": "Maximum accepted supply-temperature setpoint",
        "check.accepted_dp_min": "Minimum accepted differential-pressure setpoint",
        "check.accepted_dp_max": "Maximum accepted differential-pressure setpoint",
        "metric.peak_gpu_temperature_c": "Peak equivalent hotspot temperature (°C)",
        "metric.gpu_temperature_variance_k2": "GPU temperature variance (K²)",
        "metric.coolant_return_overshoot_k": "Coolant return overshoot (K)",
        "metric.max_supply_deviation_k": "Maximum tracking error to ramped setpoint (K)",
        "metric.max_accepted_target_deviation_k": "Maximum deviation from final accepted target (K)",
        "metric.controller_response_delay_s": "Valve response delay (s)",
        "metric.pump_energy_kwh": "Pump energy (kWh)",
        "metric.facility_cooling_energy_kwh": "Facility cooling energy (kWh)",
        "metric.minimum_thermal_margin_k": "Minimum thermal margin (K)",
        "metric.controller_oscillation_index": "Pump command step-change standard deviation (percentage points/step)",
        "metric.controller_valve_oscillation_index": "Valve command step-change standard deviation (percentage points/step)",
        "metric.throttle_timestep_count": "Throttle timestep count",
        "metric.steady_high_heat_balance_error_pct": "Steady heat-balance error (%)",
    },
    "zh-CN": {
        "timeline.title": "控制响应时间线——首次负载阶跃",
        "timeline.time": "相对负载阶跃的时间 (秒)",
        "timeline.axis_power": "GPU 功率 (kW)",
        "timeline.axis_temp_target": "供液温度目标 (°C)",
        "timeline.axis_dp_target": "压差目标 (kPa)",
        "timeline.axis_pump": "泵速 (%)",
        "timeline.axis_valve": "阀门开度 (%)",
        "timeline.axis_temperature": "PLC 温度输入\n相对基线变化 (K)",
        "timeline.axis_pressure": "PLC 压差输入\n相对基线变化 (kPa)",
        "timeline.accepted": "接受的最终目标",
        "timeline.actual": "渐变控制设定值",
        "timeline.power": "GPU 功率变化 ≥ 1kW",
        "timeline.intent": "阶跃后首次更新前馈建议（反馈工况仅影子计算）",
        "timeline.pump": "泵速变化 ≥ 2 个百分点",
        "timeline.valve": "阀位变化 ≥ 2 个百分点",
        "timeline.temperature": "PLC 温度输入偏离基线 ≥ 0.1K",
        "timeline.pressure": "PLC 压差输入偏离基线 ≥ 0.2kPa",
        "timeline.delay": "距负载阶跃的时间 (秒)",
        "timeline.none": "高负载窗口内未达到",
        "timeline.explanation": (
            "GPU 功率 → 估算液冷热负荷 → 上层控制目标 → PLC 泵速与阀位指令。"
            "左列为仅反馈，右列为功率前馈。图中放大首次阶跃前 30 秒至后 180 秒，"
            "下表统计完整的首次高负载阶段。紫色线表示相对阶跃前 60 秒均值"
            "（不足时取可用样本）首次达到下列绝对变化阈值的时刻。"
            "反馈工况更新前馈建议不代表应用建议。温度、压差曲线是 PLC 在本次动作前"
            "实际读到的模型输入，与动作后的模型输出区分。"
        ),
        "timeline.limits": (
            "这些时刻是仿真信号越过指定阈值的时间，不是传感器感知延迟或因果证明。"
            "前馈动作本身也会改变温度、压差。模型未模拟传感器采集与通信延迟；"
            "静态水力阻力不随 GPU 热负荷改变。当前功率前馈响应已经发生的负载变化，"
            "尚未预测未来任务，也未以结温作为控制输入。温度与压力反馈始终参与调节。"
        ),
        "report.title": "C2C-DTB V0.1 基准测试",
        "report.page_title": "C2C-DTB 报告",
        "report.explanation": (
            "两组在 {step_s:g} 秒前使用相同反馈控制，负载阶跃时才启用前馈。"
            "设定值延迟和阀门响应延迟分别计算；两组阀门响应均以变化达到 2 个百分点判定。"
            "供液偏差检查针对实际渐变控制设定值；相对最终接受目标的偏差单列，"
            "该项 PASS 不代表最终目标偏差也已达标。"
        ),
        "report.kpis": "关键指标",
        "report.threshold_checks": "阈值检查",
        "report.case": "工况",
        "report.metric": "指标",
        "report.value": "数值",
        "report.limit": "阈值",
        "report.status": "状态",
        "report.pass": "通过",
        "report.fail": "超限",
        "report.invalid": "数据无效",
        "report.overall": "综合状态",
        "report.plot_alt": "基准测试对比图",
        "metric.validation_errors": "无效的数据列或采样窗口",
        "metric.startup_supply_deviation_k": "启动阶段供液偏差 (K)",
        "metric.post_step_supply_deviation_k": "阶跃后供液偏差 (K)",
        "metric.setpoint_response_delay_s": "设定值响应延迟 (秒)",
        "report.interpretation_limits": "结果解释边界",
        "report.limits_text": (
            "本结果仅展示模型行为与时序，不代表已验证的 GB300 或 CDU 性能。投入运行前，"
            "必须用 FAT/SAT 数据替换假设参数并完成验证。GPU 字段表示包含 CPU 等液冷热的"
            "聚合等效热点；启动初态并非全系统联合稳态。稳态热平衡检查不代表已验证管路储能的瞬态守恒。"
        ),
        "claims.generic": "设备参数均为通用假设；结果用于工程对比，不代表 OEM 性能预测。",
        "case.feedback_only": "仅反馈控制",
        "case.guarded_feedforward": "受保护前馈控制",
        "plot.gpu_power_kw": "GPU 功率 (kW)",
        "plot.gpu_temperature_c": "聚合等效热点温度 (°C)",
        "plot.secondary_supply_temp_c": "二次侧供液温度 (°C)",
        "plot.secondary_return_temp_c": "二次侧回液温度 (°C)",
        "plot.secondary_flow_m3h": "二次侧流量 (m³/h)",
        "plot.pump_power_kw": "泵功率 (kW)",
        "plot.time": "仿真时间 (s)",
        "plot.ramped_target": "前馈渐变控制设定值",
        "plot.final_target": "前馈最终目标",
        "plot.title": "C2C-DTB V0.1：仅反馈控制与受保护 GPU 功率前馈控制对比",
        "check.gpu_temperature": "聚合等效热点峰值温度",
        "check.supply_deviation": "相对渐变控制设定值的最大跟踪偏差",
        "check.heat_balance": "稳态热平衡误差",
        "check.valve_oscillation": "阀门指令步间变化标准差",
        "check.pump_speed_min": "泵速最小值",
        "check.pump_speed_max": "泵速最大值",
        "check.valve_position_min": "阀位最小值",
        "check.valve_position_max": "阀位最大值",
        "check.accepted_temp_min": "PLC 接受的最低供液温度设定值",
        "check.accepted_temp_max": "PLC 接受的最高供液温度设定值",
        "check.accepted_dp_min": "PLC 接受的最低压差设定值",
        "check.accepted_dp_max": "PLC 接受的最高压差设定值",
        "metric.peak_gpu_temperature_c": "聚合等效热点峰值温度 (°C)",
        "metric.gpu_temperature_variance_k2": "GPU 温度方差 (K²)",
        "metric.coolant_return_overshoot_k": "冷却液回水温度超调 (K)",
        "metric.max_supply_deviation_k": "相对渐变控制设定值的最大跟踪偏差 (K)",
        "metric.max_accepted_target_deviation_k": "相对最终接受目标的最大偏差 (K)",
        "metric.controller_response_delay_s": "阀门响应延迟 (秒)",
        "metric.pump_energy_kwh": "泵耗电量 (kWh)",
        "metric.facility_cooling_energy_kwh": "设施冷却耗电量 (kWh)",
        "metric.minimum_thermal_margin_k": "最小热裕量 (K)",
        "metric.controller_oscillation_index": "泵指令步间变化标准差 (百分点/步)",
        "metric.controller_valve_oscillation_index": "阀门指令步间变化标准差 (百分点/步)",
        "metric.throttle_timestep_count": "触发节流的时间步数",
        "metric.steady_high_heat_balance_error_pct": "高负载稳态热平衡误差 (%)",
    },
}


def normalize_locale(locale: str) -> str:
    normalized = locale.replace("_", "-").lower()
    aliases = {"en": "en", "en-us": "en", "zh": "zh-CN", "zh-cn": "zh-CN"}
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported locale {locale!r}; choose one of: {', '.join(SUPPORTED_LOCALES)}"
        ) from exc


def translate(key: str, locale: str = "en", **values: object) -> str:
    language = normalize_locale(locale)
    text = _TRANSLATIONS[language].get(key, _TRANSLATIONS["en"].get(key, key))
    return text.format(**values)
