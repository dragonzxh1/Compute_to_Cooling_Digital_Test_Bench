"""Registered feedback-only generic fixture; no feedforward or hardware claims."""

import json
from dataclasses import replace
from pathlib import Path

from v0_2.actuators.pump import PumpActuatorConfig
from v0_2.control.inner_loop import InnerConfig
from v0_2.control.outer_feedback import OuterConfig
from v0_2.control.pid import PIDConfig
from v0_2.measurement.local_sensor import SensorConfig
from v0_2.plant.controlled_loop import ControlClocks, Disturbance, run_feedback
from v0_2.plant.fixtures import physical_fixture
from v0_2.safety.supervisor import SafetyPolicy

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_tuning_registration.json"


def fixture_configs(inner=None, outer=None, physics_ns=200_000_000):
    inner = inner or {"kp": 0.00001, "ki": 0.000002, "kd": 0.0}
    outer = outer or {"kp": 2000.0, "ki": 40.0, "kd": 0.0}
    clocks = ControlClocks(physics_ns, 1_000_000_000, 200_000_000, 200_000_000, 200_000_000)
    sensor = SensorConfig(200_000_000, 0)
    actuator = PumpActuatorConfig(0.3, 0.9, 1.0, 0.2, 200_000_000)
    outer_cfg = OuterConfig(PIDConfig(**outer, sample_ns=clocks.outer_ns, lower=-15000, upper=25000, integral_limit=25000, tracking_gain=0.2), 25725, 305)
    inner_cfg = InnerConfig(PIDConfig(**inner, sample_ns=clocks.plc_ns, lower=0.3, upper=0.9, integral_limit=0.9, tracking_gain=2.0))
    safety = SafetyPolicy(305, 340, 335, 345, 333, 343, 0.02, 60000, 25725, 6000, 50000, 30000, 0.5)
    return clocks, sensor, actuator, outer_cfg, inner_cfg, safety


def scenario_events(scenario_id):
    if scenario_id == "TUNE-01-load":
        return (Disturbance(10_000_000_000, power_each_w=240),)
    if scenario_id == "TUNE-02-fws-temperature":
        return (Disturbance(10_000_000_000, fws_inlet_k=294),)
    if scenario_id == "TUNE-03-fws-flow":
        return (Disturbance(10_000_000_000, primary_flow_kg_s=0.28),)
    if scenario_id == "TUNE-04-branch-restriction":
        return (Disturbance(10_000_000_000, branch_zero_k_multiplier=1.5),)
    if scenario_id == "HOLDOUT-01-combined":
        return (
            Disturbance(10_000_000_000, power_each_w=240),
            Disturbance(25_000_000_000, fws_inlet_k=294),
            Disturbance(40_000_000_000, branch_zero_k_multiplier=1.5),
        )
    raise ValueError(scenario_id)


def run_scenario(scenario_id, *, inner=None, outer=None, physics_ns=200_000_000):
    registered = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    if scenario_id in registered["training_ids"]:
        duration = registered["training_duration_ns"]
    elif scenario_id in registered["holdout_ids"]:
        duration = registered["holdout_duration_ns"]
    else:
        raise ValueError("unregistered scenario")
    plant, controls = physical_fixture(branch_count=2, power_each=120)
    configs = fixture_configs(inner, outer, physics_ns)
    return run_feedback(plant, replace(controls, speed_actual=replace(controls.speed_actual, value=0.7, valid_range=(0.7, 0.7))), duration, *configs, disturbances=scenario_events(scenario_id))


def main():
    result = run_scenario("TUNE-01-load")
    print(json.dumps({"scenario": "TUNE-01-load", "metrics": result.metrics(), "events": result.events}, indent=2))


if __name__ == "__main__":
    main()
