"""Read-only Phase 4.1 control-authority audit of accepted physical steps."""

from dataclasses import dataclass
from hashlib import sha256

from v0_2.plant.loop import assert_coldplate_flow_wiring
from v0_2.thermal.coldplate import FlowInput
from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import SolverStatus, ValidityStatus, require


@dataclass(frozen=True)
class ControlAuthorityTrace:
    time_ns: int
    end_ns: int
    pump_speed_actual_fraction: float
    pump_dp_pa: float
    total_mass_flow_kg_s: float
    branch_id: str
    branch_mass_flow_kg_s: float
    coldplate_rth_k_w: float
    plate_temperature_k: float
    local_coolant_temperature_k: float
    plate_to_coolant_heat_w: float
    device_temperature_k: float
    package_temperature_k: float
    branch_return_temperature_k: float
    hx_secondary_heat_w: float
    pump_electrical_w: float
    pump_state_id: str
    hydraulic_solution_id: str
    branch_flow_record_id: str
    coldplate_evaluation_id: str
    thermal_step_id: str


def traces_for_step(plant, before, accepted, controls):
    """Use the *matrix-used* flow/R and accepted flux; never re-solve thermal physics."""
    require(
        accepted.solver_status == SolverStatus.CONVERGED
        and accepted.ledger is not None
        and accepted.hydraulic is not None
        and accepted.next_state.time_ns > before.time_ns,
        "CONTROL_AUTHORITY_PATH_INVALID",
        "accepted interval required",
        ValidityStatus.MODEL_INVALID,
    )
    h = accepted.hydraulic
    speed = controls.speed_actual.si("fraction")
    density = plant.heat_exchanger.secondary_fluid.density.value
    dt_s = (accepted.next_state.time_ns - before.time_ns) / 1e9
    solution_payload = (
        before.time_ns,
        accepted.next_state.time_ns,
        speed,
        h.pump_head_pa,
        h.total_flow_m3_s,
        h.branch_flows_m3_s,
    )
    hydraulic_id = "hydraulic:" + sha256(repr(solution_payload).encode()).hexdigest()[:20]
    pump_id = f"pump:{before.time_ns}:{speed:.17g}"
    step_id = f"thermal:{before.time_ns}:{accepted.next_state.time_ns}:{hydraulic_id}"
    interfaces = {e.interface_id: e for e in plant.interfaces}
    heat_j = dict(accepted.ledger.interface_heat_j)
    traces = []
    for use in accepted.coldplate_uses:
        branch = use.branch_index
        require(
            dict(plant.coldplate_branches).get(use.interface_id) == branch,
            "CONTROL_AUTHORITY_PATH_INVALID",
            "wrong-branch coldplate record",
            ValidityStatus.MODEL_INVALID,
        )
        edge = interfaces[use.interface_id]
        expected = h.branch_flows_m3_s[branch] * density
        # The check uses the same accepted matrix input, not a newly evaluated Rth.
        flow = FlowInput(
            ParameterRecord(
                f"audit:{use.interface_id}",
                use.local_mass_flow_kg_s,
                "kg/s",
                "ENGINEERING_ASSUMPTION",
                "ACCEPTED_THERMAL_MATRIX",
                0.0,
                plant.provenance.date,
                (use.local_mass_flow_kg_s, use.local_mass_flow_kg_s),
                "UNVALIDATED",
            ),
            plant.heat_exchanger.secondary_fluid.fluid_id,
        )
        assert_coldplate_flow_wiring(flow, branch, h, density)
        require(
            use.conductance_w_k > 0
            and abs(use.conductance_w_k * use.endpoint_resistance_k_w - 1) <= 1e-12,
            "CONTROL_AUTHORITY_PATH_INVALID",
            "matrix conductance/Rth mismatch",
            ValidityStatus.MODEL_INVALID,
        )
        final = accepted.next_state.by_id
        q = heat_j[use.interface_id] / dt_s
        matrix_q = use.conductance_w_k * (
            final[edge.hot_node_id].temperature_k - final[edge.cold_node_id].temperature_k
        )
        require(
            abs(q - matrix_q) <= max(1e-6, 1e-9 * abs(q)),
            "CONTROL_AUTHORITY_PATH_INVALID",
            "recorded heat does not use matrix conductance",
            ValidityStatus.MODEL_INVALID,
        )
        branch_id = edge.interface_id.rsplit(":", 1)[0]
        for suffix in ("die", "package", "return"):
            require(
                f"{branch_id}:{suffix}" in final,
                "CONTROL_AUTHORITY_PATH_INVALID",
                f"missing audit observation {branch_id}:{suffix}",
                ValidityStatus.MODEL_INVALID,
            )
        flow_id = f"{hydraulic_id}:branch:{branch}:{expected:.17g}"
        cp_id = f"{flow_id}:cp:{use.interface_id}:{use.endpoint_resistance_k_w:.17g}"
        traces.append(
            ControlAuthorityTrace(
                before.time_ns,
                accepted.next_state.time_ns,
                speed,
                h.pump_head_pa,
                h.total_flow_m3_s * density,
                branch_id,
                use.local_mass_flow_kg_s,
                use.endpoint_resistance_k_w,
                final[edge.hot_node_id].temperature_k,
                final[edge.cold_node_id].temperature_k,
                q,
                final[f"{branch_id}:die"].temperature_k,
                final[f"{branch_id}:package"].temperature_k,
                final[f"{branch_id}:return"].temperature_k,
                accepted.hx.secondary_out_w,
                accepted.pump.electrical_w,
                pump_id,
                hydraulic_id,
                flow_id,
                cp_id,
                step_id,
            )
        )
    require(
        len(traces) == len(plant.coldplate_branches),
        "CONTROL_AUTHORITY_PATH_INVALID",
        "missing branch audit",
        ValidityStatus.MODEL_INVALID,
    )
    return tuple(traces)


def traces_for_run(run):
    """Resolve held event controls at each accepted interval start, including right-side events."""
    plant, initial_controls, _, events = run.qualification_inputs
    controls = initial_controls
    cursor = 0
    rows = []
    for before, accepted in zip(run.states, run.accepted):
        if cursor < len(events) and before.time_ns == events[cursor].time_ns:
            controls = events[cursor].controls
            cursor += 1
        rows.extend(traces_for_step(plant, before, accepted, controls))
    return tuple(rows)
