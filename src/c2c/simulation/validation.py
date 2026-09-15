from __future__ import annotations

from collections.abc import Mapping
from math import ceil, floor, isfinite
from typing import Any

from c2c.core.windows import benchmark_windows


class ScenarioValidationError(ValueError):
    """Raised when a scenario can produce undefined or misleading simulation results."""


def _number(config: Mapping[str, Any], path: str) -> float:
    value: Any = config
    try:
        for part in path.split("."):
            value = value[part]
        number = float(value)
    except (KeyError, TypeError, ValueError) as exc:
        raise ScenarioValidationError(f"{path} must be a finite number") from exc
    if not isfinite(number):
        raise ScenarioValidationError(f"{path} must be a finite number")
    return number


def _bounded(config: Mapping[str, Any], path: str, minimum: float, maximum: float) -> None:
    value = _number(config, path)
    if not minimum <= value <= maximum:
        raise ScenarioValidationError(f"{path} must be between {minimum:g} and {maximum:g}")


def _positive(config: Mapping[str, Any], path: str, *, allow_zero: bool = False) -> None:
    value = _number(config, path)
    valid = value >= 0 if allow_zero else value > 0
    if not valid:
        operator = "non-negative" if allow_zero else "greater than zero"
        raise ScenarioValidationError(f"{path} must be {operator}")


def _ordered(config: Mapping[str, Any], low_path: str, high_path: str) -> None:
    low, high = _number(config, low_path), _number(config, high_path)
    if low > high:
        raise ScenarioValidationError(f"{low_path} must not exceed {high_path}")


def validate_scenario(config: Mapping[str, Any]) -> None:
    _positive(config, "time.dt_s")
    _positive(config, "time.duration_s")

    phases = config.get("workload", {}).get("phases")
    if not isinstance(phases, list) or len(phases) < 2:
        raise ScenarioValidationError("workload.phases must contain at least two phases")
    starts: list[float] = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, Mapping):
            raise ScenarioValidationError(f"workload.phases[{index}] must be a mapping")
        try:
            start = float(phase.get("start_s", float("nan")))
            utilization = float(phase.get("utilization_pct", float("nan")))
        except (TypeError, ValueError) as exc:
            raise ScenarioValidationError(
                f"workload.phases[{index}] values must be finite numbers"
            ) from exc
        if not isfinite(start) or start < 0:
            raise ScenarioValidationError(f"workload.phases[{index}].start_s must be non-negative")
        if not isfinite(utilization) or not 0 <= utilization <= 100:
            raise ScenarioValidationError(
                f"workload.phases[{index}].utilization_pct must be between 0 and 100"
            )
        starts.append(start)
    if starts[0] != 0 or starts != sorted(set(starts)):
        raise ScenarioValidationError(
            "workload phase start times must begin at 0 and be strictly increasing"
        )
    duration_s = _number(config, "time.duration_s")
    dt_s = _number(config, "time.dt_s")
    if starts[-1] > duration_s:
        raise ScenarioValidationError("workload phase start times must be within the duration")
    high_end_s = starts[2] if len(starts) > 2 else duration_s
    if starts[1] < dt_s or high_end_s - starts[1] < dt_s:
        raise ScenarioValidationError(
            "benchmark phases must provide sampled pre-step and high-load windows"
        )
    for (begin, end), minimum in zip(benchmark_windows(config), (1, 2, 1), strict=True):
        count = max(0, min(ceil(end / dt_s), floor(duration_s / dt_s) + 1) - ceil(begin / dt_s))
        if count < minimum:
            raise ScenarioValidationError("benchmark windows have insufficient sampled points")

    for path in (
        "compute.gpu_count",
        "compute.gpu_idle_power_w",
        "compute.gpu_max_power_w",
        "compute.gpu_power_limit_w",
        "fluid.density_kg_m3",
        "fluid.cp_j_kgk",
        "thermal.c_die_j_k",
        "thermal.c_package_j_k",
        "thermal.c_cold_plate_j_k",
        "thermal.c_coolant_j_k",
        "thermal.r_die_package_k_w",
        "thermal.r_package_plate_k_w",
        "thermal.r_plate_coolant_k_w",
        "thermal.throttle_temp_c",
        "hydraulics.pump_shutoff_dp_pa",
        "hydraulics.pump_efficiency",
        "cdu.ua_clean_w_k",
        "reporting.facility_cop",
        "reporting.limits.max_supply_deviation_k",
        "reporting.limits.max_steady_heat_balance_error_pct",
        "reporting.limits.max_valve_oscillation_index_pct",
        "lci.update_interval_s",
        "lci.target_delta_t_k",
    ):
        _positive(config, path)
    for path in (
        "compute.cpu_power_w",
        "compute.other_power_w",
        "thermal.transport_delay_s",
        "hydraulics.system_k_pa_s2_m6",
        "hydraulics.pump_k_pa_s2_m6",
        "cdu.primary_max_flow_m3_s",
        "controls.pump_ramp_pct_s",
        "controls.valve_ramp_pct_s",
        "controls.intent_timeout_s",
        "controls.dp_deadband_kpa",
        "controls.temp_deadband_k",
    ):
        _positive(config, path, allow_zero=True)
    gpu_count = _number(config, "compute.gpu_count")
    if not gpu_count.is_integer():
        raise ScenarioValidationError("compute.gpu_count must be an integer")
    if _number(config, "compute.gpu_idle_power_w") > _number(config, "compute.gpu_max_power_w"):
        raise ScenarioValidationError("compute.gpu_idle_power_w must not exceed gpu_max_power_w")
    _bounded(
        config,
        "compute.gpu_power_limit_w",
        _number(config, "compute.gpu_idle_power_w"),
        _number(config, "compute.gpu_max_power_w"),
    )
    for loop_name in ("dp_pid", "temp_pid"):
        for term in ("kp", "ki", "kd"):
            _positive(config, f"controls.{loop_name}.{term}", allow_zero=True)
    for path in ("heat_capture.alpha_gpu", "heat_capture.alpha_cpu", "heat_capture.alpha_other"):
        _bounded(config, path, 0, 1)
    _bounded(config, "hydraulics.pump_efficiency", 0.000001, 1)
    _bounded(config, "cdu.fouling_factor", 0, 1)
    for path in (
        "controls.pump_speed_min_pct",
        "controls.pump_speed_max_pct",
        "controls.valve_min_pct",
        "controls.valve_max_pct",
    ):
        _bounded(config, path, 0, 100)
    _ordered(config, "controls.pump_speed_min_pct", "controls.pump_speed_max_pct")
    _ordered(config, "controls.valve_min_pct", "controls.valve_max_pct")
    _ordered(config, "controls.supply_temp_min_c", "controls.supply_temp_max_c")
    _ordered(config, "controls.dp_min_kpa", "controls.dp_max_kpa")
    _ordered(config, "lci.min_supply_setpoint_c", "lci.max_supply_setpoint_c")
    _ordered(config, "lci.min_dp_setpoint_kpa", "lci.max_dp_setpoint_kpa")
    _bounded(
        config,
        "controls.supply_temp_setpoint_c",
        _number(config, "controls.supply_temp_min_c"),
        _number(config, "controls.supply_temp_max_c"),
    )
    _bounded(
        config,
        "controls.dp_target_kpa",
        _number(config, "controls.dp_min_kpa"),
        _number(config, "controls.dp_max_kpa"),
    )
    if (
        _number(config, "hydraulics.system_k_pa_s2_m6")
        + _number(config, "hydraulics.pump_k_pa_s2_m6")
        <= 0
    ):
        raise ScenarioValidationError("the combined hydraulic resistance must be greater than zero")
