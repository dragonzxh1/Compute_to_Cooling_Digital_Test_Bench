from dataclasses import dataclass
from math import isfinite

from c2c.controls.guardrails import clamp, deadband, rate_limit
from c2c.controls.pid import PID
from c2c.controls.supervisory import SupervisoryIntent


@dataclass(frozen=True)
class PLCOutput:
    pump_speed_pct: float
    valve_position_pct: float
    requested_temp_setpoint_c: float
    accepted_temp_setpoint_c: float
    actual_temp_setpoint_c: float
    requested_dp_kpa: float
    accepted_dp_kpa: float
    intent_status: str


class VirtualPLC:
    def __init__(self, config: dict):
        self.cfg = config
        self.pump_speed_pct = clamp(
            60.0, config["pump_speed_min_pct"], config["pump_speed_max_pct"]
        )
        self.valve_position_pct = clamp(40.0, config["valve_min_pct"], config["valve_max_pct"])
        self.dp_pid = PID(
            **config["dp_pid"],
            output_min=config["pump_speed_min_pct"],
            output_max=config["pump_speed_max_pct"],
            bias=60.0,
        )
        self.temp_pid = PID(
            **config["temp_pid"],
            output_min=config["valve_min_pct"],
            output_max=config["valve_max_pct"],
            bias=40.0,
        )

    def step(
        self,
        measured_dp_kpa: float,
        measured_supply_temp_c: float,
        dt_s: float,
        t_s: float,
        intent: SupervisoryIntent | None,
        apply_supervisory: bool,
    ) -> PLCOutput:
        if not isfinite(t_s) or t_s < 0 or not isfinite(dt_s) or dt_s < 0:
            raise ValueError("PLC time and timestep must be finite and non-negative")
        local_temp = self.cfg["supply_temp_setpoint_c"]
        local_dp = self.cfg["dp_target_kpa"]
        requested_temp, requested_dp, status = local_temp, local_dp, "SHADOW"
        if intent is not None:
            requested_temp = intent.recommended_supply_temp_setpoint_c
            requested_dp = intent.recommended_dp_kpa
        valid = (
            intent is not None
            and all(isfinite(v) for v in vars(intent).values())
            and 0 <= t_s - intent.timestamp_s <= self.cfg["intent_timeout_s"]
        )
        if apply_supervisory and valid:
            accepted_temp = clamp(
                requested_temp,
                self.cfg.get("supply_temp_min_c", 24.0),
                self.cfg.get("supply_temp_max_c", 32.0),
            )
            accepted_dp = clamp(
                requested_dp,
                self.cfg.get("dp_min_kpa", 35.0),
                self.cfg.get("dp_max_kpa", 95.0),
            )
            status = "ACCEPTED"
        else:
            accepted_temp, accepted_dp = local_temp, local_dp
            status = "LOCAL_FALLBACK" if apply_supervisory else "SHADOW"

        dp_error = deadband(accepted_dp - measured_dp_kpa, self.cfg.get("dp_deadband_kpa", 0.0))
        temp_error = deadband(
            measured_supply_temp_c - accepted_temp, self.cfg.get("temp_deadband_k", 0.0)
        )
        # Hold the affected actuator without updating PID state on sensor faults.
        pump_target = (
            self.dp_pid.step(dp_error, dt_s) if isfinite(measured_dp_kpa) else self.pump_speed_pct
        )
        valve_target = (
            self.temp_pid.step(temp_error, dt_s)
            if isfinite(measured_supply_temp_c)
            else self.valve_position_pct
        )
        if not isfinite(measured_dp_kpa) or not isfinite(measured_supply_temp_c):
            status = "INVALID_MEASUREMENT_HOLD"
        self.pump_speed_pct = rate_limit(
            pump_target, self.pump_speed_pct, self.cfg["pump_ramp_pct_s"], dt_s
        )
        self.valve_position_pct = rate_limit(
            valve_target, self.valve_position_pct, self.cfg["valve_ramp_pct_s"], dt_s
        )
        self.pump_speed_pct = clamp(
            self.pump_speed_pct,
            self.cfg["pump_speed_min_pct"],
            self.cfg["pump_speed_max_pct"],
        )
        self.valve_position_pct = clamp(
            self.valve_position_pct,
            self.cfg["valve_min_pct"],
            self.cfg["valve_max_pct"],
        )
        return PLCOutput(
            self.pump_speed_pct,
            self.valve_position_pct,
            requested_temp,
            accepted_temp,
            accepted_temp,
            requested_dp,
            accepted_dp,
            status,
        )
