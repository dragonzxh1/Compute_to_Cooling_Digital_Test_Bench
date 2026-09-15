from __future__ import annotations

SUPPORTED_LOCALES = ("en", "zh-CN")

_TRANSLATIONS = {
    "en": {
        "report.title": "C2C-DTB V0.1 benchmark",
        "report.page_title": "C2C-DTB report",
        "report.explanation": (
            "The GPU-power signal changes at {step_s:g} s. The guarded feedforward case may "
            "act before the transported coolant-return measurement changes; all L2 intents "
            "remain clamped and rate-limited by the virtual PLC."
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
        "report.interpretation_limits": "Interpretation limits",
        "report.limits_text": (
            "This demonstrates model behavior and timing, not verified GB300 or CDU "
            "performance. Replace ASSUMED parameters and validate against FAT/SAT data "
            "before operational use."
        ),
        "claims.generic": (
            "Generic assumed equipment; comparative engineering result, not OEM prediction."
        ),
        "case.feedback_only": "Feedback only",
        "case.guarded_feedforward": "Guarded feedforward",
        "plot.gpu_power_kw": "GPU power (kW)",
        "plot.gpu_temperature_c": "GPU die temperature (°C)",
        "plot.secondary_supply_temp_c": "Secondary supply (°C)",
        "plot.secondary_return_temp_c": "Secondary return (°C)",
        "plot.secondary_flow_m3h": "Secondary flow (m³/h)",
        "plot.pump_power_kw": "Pump power (kW)",
        "plot.time": "Simulation time (s)",
        "plot.title": "C2C-DTB V0.1: feedback-only vs guarded GPU-power feedforward",
        "check.gpu_temperature": "Peak GPU temperature",
        "check.supply_deviation": "Maximum supply-temperature deviation",
        "check.heat_balance": "Steady-state heat-balance error",
        "check.valve_oscillation": "Valve command oscillation index",
        "check.pump_speed_min": "Minimum pump speed",
        "check.pump_speed_max": "Maximum pump speed",
        "check.valve_position_min": "Minimum valve position",
        "check.valve_position_max": "Maximum valve position",
        "check.accepted_temp_min": "Minimum accepted supply-temperature setpoint",
        "check.accepted_temp_max": "Maximum accepted supply-temperature setpoint",
        "check.accepted_dp_min": "Minimum accepted differential-pressure setpoint",
        "check.accepted_dp_max": "Maximum accepted differential-pressure setpoint",
        "metric.peak_gpu_temperature_c": "Peak GPU temperature (°C)",
        "metric.gpu_temperature_variance_k2": "GPU temperature variance (K²)",
        "metric.coolant_return_overshoot_k": "Coolant return overshoot (K)",
        "metric.max_supply_deviation_k": "Maximum supply deviation (K)",
        "metric.controller_response_delay_s": "Controller response delay (s)",
        "metric.pump_energy_kwh": "Pump energy (kWh)",
        "metric.facility_cooling_energy_kwh": "Facility cooling energy (kWh)",
        "metric.minimum_thermal_margin_k": "Minimum thermal margin (K)",
        "metric.controller_oscillation_index": "Pump oscillation index (%/step)",
        "metric.controller_valve_oscillation_index": "Valve oscillation index (%/step)",
        "metric.throttle_timestep_count": "Throttle timestep count",
        "metric.steady_high_heat_balance_error_pct": "Steady heat-balance error (%)",
    },
    "zh-CN": {
        "report.title": "C2C-DTB V0.1 基准测试",
        "report.page_title": "C2C-DTB 报告",
        "report.explanation": (
            "GPU 功率信号在 {step_s:g} 秒发生变化。受保护的前馈工况可能在输运后的冷却液"
            "回水测量变化前提前动作；所有 L2 控制意图仍由虚拟 PLC 执行限幅和速率限制。"
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
        "report.interpretation_limits": "结果解释边界",
        "report.limits_text": (
            "本结果仅展示模型行为与时序，不代表已验证的 GB300 或 CDU 性能。投入运行前，"
            "必须用 FAT/SAT 数据替换假设参数并完成验证。"
        ),
        "claims.generic": "设备参数均为通用假设；结果用于工程对比，不代表 OEM 性能预测。",
        "case.feedback_only": "仅反馈控制",
        "case.guarded_feedforward": "受保护前馈控制",
        "plot.gpu_power_kw": "GPU 功率 (kW)",
        "plot.gpu_temperature_c": "GPU 核心温度 (°C)",
        "plot.secondary_supply_temp_c": "二次侧供液温度 (°C)",
        "plot.secondary_return_temp_c": "二次侧回液温度 (°C)",
        "plot.secondary_flow_m3h": "二次侧流量 (m³/h)",
        "plot.pump_power_kw": "泵功率 (kW)",
        "plot.time": "仿真时间 (s)",
        "plot.title": "C2C-DTB V0.1：仅反馈控制与受保护 GPU 功率前馈控制对比",
        "check.gpu_temperature": "GPU 峰值温度",
        "check.supply_deviation": "最大供液温度偏差",
        "check.heat_balance": "稳态热平衡误差",
        "check.valve_oscillation": "阀门指令振荡指数",
        "check.pump_speed_min": "泵速最小值",
        "check.pump_speed_max": "泵速最大值",
        "check.valve_position_min": "阀位最小值",
        "check.valve_position_max": "阀位最大值",
        "check.accepted_temp_min": "PLC 接受的最低供液温度设定值",
        "check.accepted_temp_max": "PLC 接受的最高供液温度设定值",
        "check.accepted_dp_min": "PLC 接受的最低压差设定值",
        "check.accepted_dp_max": "PLC 接受的最高压差设定值",
        "metric.peak_gpu_temperature_c": "GPU 峰值温度 (°C)",
        "metric.gpu_temperature_variance_k2": "GPU 温度方差 (K²)",
        "metric.coolant_return_overshoot_k": "冷却液回水温度超调 (K)",
        "metric.max_supply_deviation_k": "最大供液温度偏差 (K)",
        "metric.controller_response_delay_s": "控制器响应延迟 (秒)",
        "metric.pump_energy_kwh": "泵耗电量 (kWh)",
        "metric.facility_cooling_energy_kwh": "设施冷却耗电量 (kWh)",
        "metric.minimum_thermal_margin_k": "最小热裕量 (K)",
        "metric.controller_oscillation_index": "泵指令振荡指数 (%/步)",
        "metric.controller_valve_oscillation_index": "阀门指令振荡指数 (%/步)",
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
