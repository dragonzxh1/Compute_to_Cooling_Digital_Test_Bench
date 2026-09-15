import pandas as pd

from c2c.cdu.plant import CDUPlant
from c2c.compute.heat import ComputeToHeatModel
from c2c.controls.supervisory import ShadowLCI
from c2c.controls.virtual_plc import VirtualPLC
from c2c.core.time import SimulationClock
from c2c.fluids.water import ConstantFluid
from c2c.hydraulics.pump import PumpSystem
from c2c.thermal.rc_network import RCThermalModel, steady_initial_state
from c2c.thermal.transport import TransportDelay
from c2c.workloads.synthetic import SyntheticWorkloadSource


def run_case(config: dict, case_name: str, apply_supervisory: bool) -> pd.DataFrame:
    clock = SimulationClock(config["time"]["dt_s"], config["time"]["duration_s"])
    fluid = ConstantFluid(
        config["fluid"]["name"],
        config["fluid"]["density_kg_m3"],
        config["fluid"]["cp_j_kgk"],
    )
    workload = SyntheticWorkloadSource(config["workload"], config["compute"])
    heat_model = ComputeToHeatModel(config["compute"], config["heat_capture"])
    pump = PumpSystem(config["hydraulics"])
    hydraulic = pump.operating_point(60.0)
    initial_telemetry = workload.next_step(0.0)
    initial_heat = heat_model.step(initial_telemetry)
    initial_thermal = steady_initial_state(
        initial_heat.liquid_heat_w,
        config["controls"]["supply_temp_setpoint_c"],
        fluid.mass_flow(hydraulic.flow_m3_s),
        fluid.cp_j_kgk,
        config["thermal"],
    )
    thermal = RCThermalModel(config["thermal"], initial_thermal)
    delay = TransportDelay(
        config["thermal"]["transport_delay_s"], clock.dt_s, initial_thermal.coolant_return_temp_c
    )
    cdu = CDUPlant(config["cdu"], fluid.density_kg_m3, fluid.cp_j_kgk)
    plc = VirtualPLC(config["controls"])
    lci = ShadowLCI(config["lci"], pump, fluid.density_kg_m3, fluid.cp_j_kgk)
    supply_temp_c = config["controls"]["supply_temp_setpoint_c"]
    heat = initial_heat
    intent = None
    rows: list[dict] = []

    for step_index, t_s in clock.steps():
        if step_index > 0:
            thermal.step(
                heat.liquid_heat_w,
                supply_temp_c,
                fluid.mass_flow(hydraulic.flow_m3_s),
                fluid.cp_j_kgk,
                clock.dt_s,
            )
        telemetry = workload.next_step(t_s)
        heat = heat_model.step(telemetry)
        if intent is None or t_s - intent.timestamp_s >= config["lci"]["update_interval_s"]:
            intent = lci.recommend(t_s, heat)

        plc_output = plc.step(
            hydraulic.dp_pa / 1000.0,
            supply_temp_c,
            0.0 if step_index == 0 else clock.dt_s,
            t_s,
            intent,
            apply_supervisory,
        )
        hydraulic = pump.operating_point(plc_output.pump_speed_pct)
        delayed_return_c = (
            thermal.state.coolant_return_temp_c
            if step_index == 0
            else delay.step(thermal.state.coolant_return_temp_c)
        )
        cdu_exchange = cdu.step(
            delayed_return_c, hydraulic.flow_m3_s, plc_output.valve_position_pct
        )
        supply_temp_c = cdu_exchange.secondary_outlet_temp_c
        thermal_state = thermal.state
        coolant_removed_w = (
            fluid.mass_flow(hydraulic.flow_m3_s)
            * fluid.cp_j_kgk
            * max(0.0, thermal_state.coolant_return_temp_c - supply_temp_c)
        )
        rows.append(
            {
                "case": case_name,
                "timestamp_s": t_s,
                "gpu_util_pct": telemetry.gpu_util_pct,
                "gpu_power_kw": telemetry.gpu_power_w / 1000.0,
                "electrical_power_kw": heat.electrical_power_w / 1000.0,
                "liquid_heat_kw": heat.liquid_heat_w / 1000.0,
                "air_residual_heat_kw": heat.air_residual_heat_w / 1000.0,
                "gpu_temperature_c": thermal_state.gpu_die_temp_c,
                "package_temperature_c": thermal_state.package_temp_c,
                "cold_plate_temperature_c": thermal_state.cold_plate_temp_c,
                "secondary_supply_temp_c": supply_temp_c,
                "secondary_return_temp_c": thermal_state.coolant_return_temp_c,
                "transported_return_temp_c": delayed_return_c,
                "secondary_delta_t_k": thermal_state.coolant_return_temp_c - supply_temp_c,
                "secondary_flow_m3h": hydraulic.flow_m3_s * 3600.0,
                "secondary_dp_kpa": hydraulic.dp_pa / 1000.0,
                "pump_speed_pct": plc_output.pump_speed_pct,
                "pump_power_kw": hydraulic.pump_power_w / 1000.0,
                "valve_position_pct": plc_output.valve_position_pct,
                "primary_flow_m3h": config["cdu"]["primary_max_flow_m3_s"]
                * plc_output.valve_position_pct
                / 100.0
                * 3600.0,
                "primary_supply_temp_c": config["cdu"]["primary_inlet_temp_c"],
                "primary_return_temp_c": cdu_exchange.primary_outlet_temp_c,
                "heat_rejected_kw": cdu_exchange.heat_rejected_w / 1000.0,
                "coolant_heat_removed_kw": coolant_removed_w / 1000.0,
                "temperature_setpoint_c": plc_output.actual_temp_setpoint_c,
                "requested_temperature_setpoint_c": plc_output.requested_temp_setpoint_c,
                "accepted_temperature_setpoint_c": plc_output.accepted_temp_setpoint_c,
                "requested_dp_kpa": plc_output.requested_dp_kpa,
                "accepted_dp_kpa": plc_output.accepted_dp_kpa,
                "lci_predicted_heat_kw": intent.predicted_heat_kw,
                "lci_recommended_flow_m3h": intent.recommended_flow_m3_s * 3600.0,
                "lci_recommended_dp_kpa": intent.recommended_dp_kpa,
                "intent_status": plc_output.intent_status,
                "thermal_margin_k": config["thermal"]["throttle_temp_c"]
                - thermal_state.gpu_die_temp_c,
                "throttle": thermal_state.gpu_die_temp_c >= config["thermal"]["throttle_temp_c"],
            }
        )
    return pd.DataFrame(rows)


def run_benchmark(config: dict) -> pd.DataFrame:
    frames = [
        run_case(config, "feedback_only", apply_supervisory=False),
        run_case(config, "guarded_feedforward", apply_supervisory=True),
    ]
    return pd.concat(frames, ignore_index=True)
