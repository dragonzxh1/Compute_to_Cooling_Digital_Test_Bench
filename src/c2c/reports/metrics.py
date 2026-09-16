import numpy as np
import pandas as pd

from c2c.core.windows import benchmark_windows
from c2c.i18n import translate


def _first_response_delay(
    case: pd.DataFrame,
    step_s: float = 300.0,
    *,
    column: str = "valve_position_pct",
    threshold: float = 2.0,
    end_s: float | None = None,
) -> float | None:
    baseline = case[(case.timestamp_s >= step_s - 60) & (case.timestamp_s < step_s)]
    after = case[case.timestamp_s >= step_s]
    if end_s is not None:
        after = after[after.timestamp_s < end_s]
    changed = after[(after[column] - baseline[column].mean()).abs() >= threshold]
    if changed.empty:
        return None
    return float(changed.timestamp_s.iloc[0] - step_s)


def _integrate_kwh(values: pd.Series, timestamps_s: pd.Series) -> float:
    if len(values) < 2:
        return 0.0
    power = values.to_numpy(dtype=float)
    timestamps = timestamps_s.to_numpy(dtype=float)
    # Engine commands and loads are held over [t_i, t_{i+1}).
    interval_energy_kw_s = power[:-1] * np.diff(timestamps)
    return float(interval_energy_kw_s.sum() / 3600.0)


def _check(
    key: str,
    actual: float,
    limit: float,
    comparison: str,
    unit: str,
    locale: str,
) -> dict:
    comparisons = {
        "<": actual < limit,
        "<=": actual <= limit,
        ">=": actual >= limit,
    }
    passed = comparisons[comparison]
    return {
        "key": key,
        "label": translate(f"check.{key}", locale),
        "actual": float(actual),
        "limit": float(limit),
        "comparison": comparison,
        "unit": unit,
        "passed": bool(passed),
    }


def case_metrics(case: pd.DataFrame, config: dict, locale: str = "en") -> dict:
    required = (
        "timestamp_s",
        "pump_power_kw",
        "heat_rejected_kw",
        "gpu_temperature_c",
        "secondary_supply_temp_c",
        "temperature_setpoint_c",
        "coolant_heat_removed_kw",
        "liquid_heat_kw",
        "valve_position_pct",
        "pump_speed_pct",
        "accepted_temperature_setpoint_c",
        "accepted_dp_kpa",
        "secondary_return_temp_c",
        "thermal_margin_k",
        "throttle",
    )
    invalid = [
        name
        for name in required
        if name not in case
        or not pd.api.types.is_numeric_dtype(case[name])
        or not np.isfinite(case[name].to_numpy(dtype=float)).all()
    ]
    if not invalid and (case.empty or (np.diff(case.timestamp_s) <= 0).any()):
        invalid.append("timestamp_s")
    if not invalid:
        dt = config["time"]["dt_s"]
        expected = np.arange(int(np.floor(config["time"]["duration_s"] / dt)) + 1) * dt
        if len(case) != len(expected) or not np.allclose(
            case.timestamp_s, expected, rtol=0, atol=1e-9
        ):
            invalid.append("timestamp_s")
    if invalid:
        return {"threshold_status": "INVALID", "threshold_checks": [], "validation_errors": invalid}
    phases = config["workload"]["phases"]
    step_s = float(phases[1]["start_s"]) if len(phases) > 1 else 0.0
    high_end_s = (
        float(phases[2]["start_s"]) if len(phases) > 2 else float(config["time"]["duration_s"])
    )
    pre, high, steady_high = [
        case[(case.timestamp_s >= lo) & (case.timestamp_s < hi)]
        for lo, hi in benchmark_windows(config)
    ]
    if pre.empty or len(high) < 2 or steady_high.empty:
        return {
            "threshold_status": "INVALID",
            "threshold_checks": [],
            "validation_errors": ["sampled_windows"],
        }
    facility_cop = float(config["reporting"]["facility_cop"])
    pump_kwh = _integrate_kwh(case.pump_power_kw, case.timestamp_s)
    facility_kwh = _integrate_kwh(case.heat_rejected_kw / facility_cop, case.timestamp_s)
    peak_gpu_temperature_c = float(case.gpu_temperature_c.max())
    max_supply_deviation_k = float(
        (case.secondary_supply_temp_c - case.temperature_setpoint_c).abs().max()
    )
    heat_balance_error_pct = float(
        100.0
        * abs(steady_high.coolant_heat_removed_kw.mean() - steady_high.liquid_heat_kw.mean())
        / max(steady_high.liquid_heat_kw.mean(), 1e-9)
    )
    valve_oscillation_index = float(np.std(np.diff(high.valve_position_pct)))
    limits = config["reporting"]["limits"]
    controls = config["controls"]
    checks = [
        _check(
            "gpu_temperature",
            peak_gpu_temperature_c,
            config["thermal"]["throttle_temp_c"],
            "<",
            "°C",
            locale,
        ),
        _check(
            "supply_deviation",
            max_supply_deviation_k,
            limits["max_supply_deviation_k"],
            "<=",
            "K",
            locale,
        ),
        _check(
            "heat_balance",
            heat_balance_error_pct,
            limits["max_steady_heat_balance_error_pct"],
            "<=",
            "%",
            locale,
        ),
        _check(
            "valve_oscillation",
            valve_oscillation_index,
            limits["max_valve_oscillation_index_pct"],
            "<=",
            "百分点/步" if locale == "zh-CN" else "percentage points/step",
            locale,
        ),
        _check(
            "pump_speed_min",
            case.pump_speed_pct.min(),
            controls["pump_speed_min_pct"],
            ">=",
            "%",
            locale,
        ),
        _check(
            "pump_speed_max",
            case.pump_speed_pct.max(),
            controls["pump_speed_max_pct"],
            "<=",
            "%",
            locale,
        ),
        _check(
            "valve_position_min",
            case.valve_position_pct.min(),
            controls["valve_min_pct"],
            ">=",
            "%",
            locale,
        ),
        _check(
            "valve_position_max",
            case.valve_position_pct.max(),
            controls["valve_max_pct"],
            "<=",
            "%",
            locale,
        ),
        _check(
            "accepted_temp_min",
            case.accepted_temperature_setpoint_c.min(),
            controls["supply_temp_min_c"],
            ">=",
            "°C",
            locale,
        ),
        _check(
            "accepted_temp_max",
            case.accepted_temperature_setpoint_c.max(),
            controls["supply_temp_max_c"],
            "<=",
            "°C",
            locale,
        ),
        _check(
            "accepted_dp_min",
            case.accepted_dp_kpa.min(),
            controls["dp_min_kpa"],
            ">=",
            "kPa",
            locale,
        ),
        _check(
            "accepted_dp_max",
            case.accepted_dp_kpa.max(),
            controls["dp_max_kpa"],
            "<=",
            "kPa",
            locale,
        ),
    ]
    return {
        "peak_gpu_temperature_c": peak_gpu_temperature_c,
        "gpu_temperature_variance_k2": float(case.gpu_temperature_c.var()),
        "coolant_return_overshoot_k": float(
            high.secondary_return_temp_c.max() - pre.secondary_return_temp_c.mean()
        ),
        "max_supply_deviation_k": max_supply_deviation_k,
        "max_accepted_target_deviation_k": float(
            (case.secondary_supply_temp_c - case.accepted_temperature_setpoint_c).abs().max()
        ),
        "startup_supply_deviation_k": float(
            (
                case[case.timestamp_s < step_s].secondary_supply_temp_c
                - case[case.timestamp_s < step_s].temperature_setpoint_c
            )
            .abs()
            .max()
        ),
        "post_step_supply_deviation_k": float(
            (
                case[case.timestamp_s >= step_s].secondary_supply_temp_c
                - case[case.timestamp_s >= step_s].temperature_setpoint_c
            )
            .abs()
            .max()
        ),
        "controller_response_delay_s": _first_response_delay(case, step_s, end_s=high_end_s),
        "setpoint_response_delay_s": _first_response_delay(
            case, step_s, column="temperature_setpoint_c", threshold=0.25, end_s=high_end_s
        ),
        "pump_energy_kwh": pump_kwh,
        "facility_cooling_energy_kwh": facility_kwh,
        "minimum_thermal_margin_k": float(case.thermal_margin_k.min()),
        "controller_oscillation_index": float(np.std(np.diff(high.pump_speed_pct))),
        "controller_valve_oscillation_index": valve_oscillation_index,
        "throttle_timestep_count": int(case.throttle.sum()),
        "steady_high_heat_balance_error_pct": heat_balance_error_pct,
        "threshold_status": "PASS" if all(check["passed"] for check in checks) else "FAIL",
        "threshold_checks": checks,
    }


def benchmark_summary(frame: pd.DataFrame, config: dict, locale: str = "en") -> dict:
    metrics = {
        name: case_metrics(case, config, locale) for name, case in frame.groupby("case", sort=False)
    }
    a, b = metrics["feedback_only"], metrics["guarded_feedforward"]
    valid = all(m["threshold_status"] != "INVALID" for m in metrics.values())
    return {
        "scenario": config["name"],
        "locale": locale,
        "claims": translate("claims.generic", locale),
        "cases": metrics,
        "comparison": None
        if not valid
        else {
            "peak_gpu_temperature_change_k": b["peak_gpu_temperature_c"]
            - a["peak_gpu_temperature_c"],
            "pump_energy_change_pct": (
                100.0 * (b["pump_energy_kwh"] / a["pump_energy_kwh"] - 1.0)
                if a["pump_energy_kwh"] > 0
                else None
            ),
            "response_delay_improvement_s": (
                None
                if a["controller_response_delay_s"] is None
                or b["controller_response_delay_s"] is None
                else a["controller_response_delay_s"] - b["controller_response_delay_s"]
            ),
        },
    }
