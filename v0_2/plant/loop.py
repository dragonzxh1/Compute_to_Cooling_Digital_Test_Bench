from dataclasses import dataclass, replace
from enum import StrEnum
from math import fsum

import numpy as np

from v0_2.cdu.heat_exchanger import evaluate
from v0_2.coolant.advection import AdvectiveEnergy, AdvectiveLink
from v0_2.hydraulics.pump import pump_energy
from v0_2.hydraulics.solver import solve
from v0_2.thermal.coldplate import FlowInput, canonical_layer
from v0_2.thermal.interfaces import InterfaceKind
from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import SolverStatus, ThermalError, ValidityStatus, require


class TopologyMode(StrEnum):
    THERMAL_VALIDATION_BATH = "THERMAL_VALIDATION_BATH"
    PHYSICAL_COOLANT_LOOP = "PHYSICAL_COOLANT_LOOP"


def preflight_coolant_path(
    interfaces, connections, legacy_fifo_enabled=False, pump_hydraulic_heat_at_pump=False
):
    bath = any(
        e.external_boundary_id in {"bath", "THERMAL_VALIDATION_BATH"}
        or (e.external_boundary_id is not None and e.boundary_medium == "LIQUID")
        for e in interfaces
    )
    advective = bool(connections)
    require(
        not (bath and advective),
        "THERMAL_PATH_DOUBLE_COUNT",
        "validation bath and physical advection are mutually exclusive",
    )
    require(
        not (advective and legacy_fifo_enabled),
        "TRANSPORT_DOUBLE_COUNT",
        "fixed FIFO and finite volumes cannot own the same path",
    )
    require(
        not (advective and pump_hydraulic_heat_at_pump),
        "PUMP_HEAT_DOUBLE_COUNT",
        "hydraulic work dissipates only at passive resistance receivers",
    )
    require(bath or advective, "PLANT_TOPOLOGY", "no declared coolant path")
    return TopologyMode.PHYSICAL_COOLANT_LOOP if advective else TopologyMode.THERMAL_VALIDATION_BATH


@dataclass(frozen=True)
class FluidConnection:
    link_id: str
    from_volume_id: str
    to_volume_id: str
    branch_index: int | None = None


@dataclass(frozen=True)
class PlantState:
    solids: tuple
    volumes: tuple
    time_ns: int = 0

    def __post_init__(self):
        require(type(self.time_ns) is int and self.time_ns >= 0, "INVALID_TIME", "plant epoch")
        ids = [n.node_id for n in self.solids] + [v.volume_id for v in self.volumes]
        owners = [n.storage_owner_id for n in self.solids] + [
            v.storage_owner_id for v in self.volumes
        ]
        require(
            len(ids) == len(set(ids)) and len(owners) == len(set(owners)),
            "VOLUME_OWNERSHIP_DUPLICATE",
            "one state per physical inventory",
        )

    @property
    def by_id(self):
        return {**{n.node_id: n for n in self.solids}, **{v.volume_id: v for v in self.volumes}}


@dataclass(frozen=True)
class PhysicalPlant:
    initial_state: PlantState
    interfaces: tuple
    connections: tuple[FluidConnection, ...]
    coldplate_branches: tuple[tuple[str, int], ...]
    hydraulic_graph: object
    pump_curve: object
    pump_drive: object
    heat_exchanger: object
    source_map: object
    cdu_volume_id: str
    volume_pressure_nodes: tuple[tuple[str, str], ...]
    provenance: ParameterRecord
    pressure_reference_pa: ParameterRecord
    legacy_fifo_enabled: bool = False
    pump_hydraulic_heat_at_pump: bool = False

    def __post_init__(self):
        require(
            preflight_coolant_path(
                self.interfaces,
                self.connections,
                self.legacy_fifo_enabled,
                self.pump_hydraulic_heat_at_pump,
            )
            == TopologyMode.PHYSICAL_COOLANT_LOOP,
            "PLANT_TOPOLOGY",
            "advection required",
        )
        ids = self.initial_state.by_id
        require(self.pressure_reference_pa.si("Pa") > 0, "INVALID_PRESSURE", "reference")
        solids = {n.node_id for n in self.initial_state.solids}
        liquids = {v.volume_id for v in self.initial_state.volumes}
        require(self.cdu_volume_id in liquids, "PLANT_TOPOLOGY", "CDU volume missing")
        require(
            set(dict(self.volume_pressure_nodes)) == liquids
            and len(self.volume_pressure_nodes) == len(liquids)
            and all(
                p in {n.node_id for n in self.hydraulic_graph.nodes}
                for _, p in self.volume_pressure_nodes
            ),
            "PLANT_TOPOLOGY",
            "volume pressure junction map",
        )
        require(
            len({c.link_id for c in self.connections}) == len(self.connections),
            "DUPLICATE_FLUX",
            "fluid link",
        )
        require(
            all(
                c.from_volume_id in liquids
                and c.to_volume_id in liquids
                and c.from_volume_id != c.to_volume_id
                for c in self.connections
            ),
            "PLANT_TOPOLOGY",
            "connection endpoint",
        )
        require(
            len({e.interface_id for e in self.interfaces}) == len(self.interfaces),
            "DUPLICATE_FLUX",
            "thermal interface",
        )
        require(
            len({e.owner_id for e in self.interfaces}) == len(self.interfaces),
            "DUPLICATE_INTERFACE_OWNER",
            "thermal owner",
        )
        require(
            len({canonical_layer(layer) for e in self.interfaces for layer in e.included_layer_ids})
            == sum(len(e.included_layer_ids) for e in self.interfaces),
            "THERMAL_RESISTANCE_OVERLAP",
            "physical plate layers",
        )
        for e in self.interfaces:
            require(e.hot_node_id in solids, "PLANT_TOPOLOGY", e.interface_id)
            require(
                e.cold_node_id in ids or e.external_boundary_id == "ambient",
                "PLANT_TOPOLOGY",
                e.interface_id,
            )
        cp_map = dict(self.coldplate_branches)
        cp_ids = {
            e.interface_id
            for e in self.interfaces
            if e.kind == InterfaceKind.COLDPLATE_FLOW_DEPENDENT
        }
        require(
            set(cp_map) == cp_ids and len(cp_map) == len(self.coldplate_branches),
            "FLOW_CONFIG",
            "coldplate branch map",
        )
        require(
            all(0 <= index < len(self.hydraulic_graph.branches) for index in cp_map.values()),
            "FLOW_CONFIG",
            "branch index",
        )
        require(
            all(
                v.coolant_ref == self.heat_exchanger.secondary_fluid.fluid_id
                for v in self.initial_state.volumes
            ),
            "COOLANT_MISMATCH",
            "secondary loop",
        )
        require(
            self.pump_drive.liquid_receiver_id in liquids,
            "LOSS_DESTINATION",
            "pump drive coolant receiver",
        )
        require(
            all(
                e.receiver_id in liquids or e.liquid_fraction.value == 0
                for e in self.hydraulic_graph.passive_edges
            ),
            "LOSS_DESTINATION",
            "passive receiver",
        )
        require(
            all(e.coefficient.value > 0 for e in self.hydraulic_graph.passive_edges),
            "INVALID_K",
            "passive graph",
        )
        # All pressure junctions and all physical volumes must carry their own balance.
        require(len(self.initial_state.volumes) >= 2, "PLANT_TOPOLOGY", "finite loop inventories")


@dataclass(frozen=True)
class PlantInput:
    speed_actual: ParameterRecord
    primary_mass_flow: ParameterRecord
    fws_inlet_temperature: ParameterRecord
    ambient_temperature: ParameterRecord
    electrical_leaves: tuple


@dataclass(frozen=True)
class PlantEnergyLedger:
    source_j: float
    stored_change_j: float
    air_export_j: float
    hx_export_j: float
    pump_electrical_j: float
    pump_hydraulic_j: float
    pump_heat_liquid_j: float
    pump_heat_ambient_j: float
    full_loop_residual_j: float
    node_residuals_j: tuple[tuple[str, float], ...]
    node_scales_j: tuple[tuple[str, float], ...]
    volume_mass_residuals_kg_s: tuple[tuple[str, float], ...]
    volume_mass_incident_kg_s: tuple[tuple[str, float], ...]
    interface_heat_j: tuple[tuple[str, float], ...]
    advective_heat: tuple[AdvectiveEnergy, ...]
    max_mass_node_residual_kg_s: float
    max_mass_volume_residual_kg_s: float


@dataclass(frozen=True)
class ColdplateUse:
    """Read-only record of the flow and conductance used by the thermal matrix."""

    interface_id: str
    branch_index: int
    local_mass_flow_kg_s: float
    endpoint_resistance_k_w: float
    conductance_w_k: float


@dataclass(frozen=True)
class PlantStep:
    next_state: PlantState
    hydraulic: object | None
    pump: object | None
    hx: object | None
    ledger: PlantEnergyLedger | None
    solver_status: SolverStatus
    validity_status: ValidityStatus
    diagnostics: tuple[str, ...]
    coldplate_uses: tuple[ColdplateUse, ...] = ()


def assert_coldplate_flow_wiring(flow: FlowInput, branch_index, hydraulic, density_kg_m3):
    """Fail if the constitutive input is not this interval's hydraulic branch flow."""
    require(0 <= branch_index < len(hydraulic.branch_flows_m3_s), "FLOW_CONFIG", "branch")
    expected = hydraulic.branch_flows_m3_s[branch_index] * density_kg_m3
    actual = flow.mass_flow.si("kg/s")
    require(
        abs(actual - expected) <= 1e-9 + 1e-8 * abs(expected),
        "CONTROL_AUTHORITY_PATH_INVALID",
        f"branch {branch_index}: used {actual}, hydraulic {expected}",
        ValidityStatus.MODEL_INVALID,
    )


def _coldplate_flow_from_hydraulic(edge, branch_index, hydraulic, fluid, plant):
    branch_m = hydraulic.branch_flows_m3_s[branch_index] * fluid.density.value
    return FlowInput(
        ParameterRecord(
            f"derived:{edge.interface_id}",
            branch_m,
            "kg/s",
            "ENGINEERING_ASSUMPTION",
            "GENERIC_HYDRAULIC_SOLVE",
            0.0,
            plant.provenance.date,
            (branch_m, branch_m),
            "UNVALIDATED",
        ),
        fluid.fluid_id,
    )


def step(plant: PhysicalPlant, state: PlantState, controls: PlantInput, dt_ns: int):
    try:
        require(type(dt_ns) is int and dt_ns >= 1000, "MINIMUM_DT", "1 microsecond")
        require(
            tuple(n.node_id for n in state.solids)
            == tuple(n.node_id for n in plant.initial_state.solids)
            and tuple(v.volume_id for v in state.volumes)
            == tuple(v.volume_id for v in plant.initial_state.volumes),
            "STATE_TOPOLOGY",
            "inventory order",
        )
        for old, new in zip(plant.initial_state.solids, state.solids):
            require(old.at_temperature(new.temperature_k) == new, "STATE_TOPOLOGY", old.node_id)
        for old, new in zip(plant.initial_state.volumes, state.volumes):
            require(
                replace(old.at_h(new.specific_enthalpy_j_kg), pressure_pa=new.pressure_pa) == new,
                "STATE_TOPOLOGY",
                old.volume_id,
            )
        dt_s = dt_ns / 1e9
        fluid = plant.heat_exchanger.secondary_fluid
        speed = controls.speed_actual.si("fraction")
        primary_flow = controls.primary_mass_flow.si("kg/s")
        fws_t = controls.fws_inlet_temperature.si("K")
        ambient_t = controls.ambient_temperature.si("K")
        hydraulic = solve(plant.hydraulic_graph, plant.pump_curve, speed, fluid.density.value)
        pump = pump_energy(
            plant.pump_drive, hydraulic.pump_head_pa, hydraulic.total_flow_m3_s, dt_s
        )
        secondary_flow = hydraulic.total_flow_m3_s * fluid.density.value
        # ε-NTU heat conductance is fixed over the held interval; the CDU volume is its
        # secondary recirculation reservoir. The rack supply is the CDU tank temperature.
        hx_basis = evaluate(
            plant.heat_exchanger,
            secondary_flow,
            primary_flow,
            state.by_id[plant.cdu_volume_id].temperature_k,
            fws_t,
        )
        hx_g = hx_basis.effectiveness * min(
            secondary_flow * fluid.specific_heat.value,
            primary_flow * plant.heat_exchanger.primary_fluid.specific_heat.value,
        )
        by_id = state.by_id
        ids = [n.node_id for n in state.solids] + [v.volume_id for v in state.volumes]
        index = {name: i for i, name in enumerate(ids)}
        c = np.array(
            [n.thermal_capacitance.value for n in state.solids]
            + [v.mass_kg.value * v.fluid.specific_heat.value for v in state.volumes]
        )
        old_t = np.array(
            [n.temperature_k for n in state.solids] + [v.temperature_k for v in state.volumes]
        )
        anchor = 300.0
        old_x = old_t - anchor
        matrix = np.diag(c)
        drive = np.zeros(len(ids))
        receipts = plant.source_map.receipts(
            controls.electrical_leaves, {n.node_id: n for n in state.solids}, state.time_ns, dt_ns
        )
        for receipt in receipts:
            drive[index[receipt.thermal_node_id]] += receipt.power_w
        cp_branch = dict(plant.coldplate_branches)
        edge_conductance = {}
        coldplate_uses = []
        for edge in plant.interfaces:
            i = index[edge.hot_node_id]
            j = index.get(edge.cold_node_id)
            cold_t = old_t[j] if j is not None else ambient_t
            flow = None
            if edge.interface_id in cp_branch:
                branch_index = cp_branch[edge.interface_id]
                flow = _coldplate_flow_from_hydraulic(edge, branch_index, hydraulic, fluid, plant)
                assert_coldplate_flow_wiring(flow, branch_index, hydraulic, fluid.density.value)
            g = edge.conductance(old_t[i], cold_t, flow)
            edge_conductance[edge.interface_id] = (g, flow)
            if flow is not None:
                coldplate_uses.append(
                    ColdplateUse(edge.interface_id, branch_index, flow.mass_flow.value, 1 / g, g)
                )
            matrix[i, i] += dt_s * g
            if j is not None:
                matrix[j, j] += dt_s * g
                matrix[i, j] -= dt_s * g
                matrix[j, i] -= dt_s * g
            else:
                drive[i] += g * (ambient_t - anchor)
        links = []
        for conn in plant.connections:
            q = (
                hydraulic.total_flow_m3_s
                if conn.branch_index is None
                else hydraulic.branch_flows_m3_s[conn.branch_index]
            ) * fluid.density.value
            links.append(
                AdvectiveLink(
                    conn.link_id,
                    conn.from_volume_id,
                    conn.to_volume_id,
                    q,
                    f"advective:{conn.link_id}",
                )
            )
        mass = {v.volume_id: 0.0 for v in state.volumes}
        mass_incident = {v.volume_id: 0.0 for v in state.volumes}
        for link in links:
            q = link.magnitude
            mass[link.donor_id] -= q
            mass[link.receiver_id] += q
            mass_incident[link.donor_id] += q
            mass_incident[link.receiver_id] += q
            k = dt_s * q * fluid.specific_heat.value
            matrix[index[link.donor_id], index[link.donor_id]] += k
            matrix[index[link.receiver_id], index[link.donor_id]] -= k
        for volume_id, value in mass.items():
            require(
                abs(value) <= 1e-9 + 1e-8 * mass_incident[volume_id],
                "MASS_BALANCE_FAIL",
                volume_id,
                ValidityStatus.MODEL_INVALID,
            )
        heat_receiver = {v.volume_id: 0.0 for v in state.volumes}
        heat_receiver[plant.pump_drive.liquid_receiver_id] += pump.loss_to_liquid_w
        for dissipation in hydraulic.dissipations:
            if dissipation.liquid_w:
                heat_receiver[dissipation.receiver_id] += dissipation.liquid_w
        for name, watts in heat_receiver.items():
            drive[index[name]] += watts
        matrix[index[plant.cdu_volume_id], index[plant.cdu_volume_id]] += dt_s * hx_g
        drive[index[plant.cdu_volume_id]] += hx_g * (fws_t - anchor)
        try:
            nx = old_x + np.linalg.solve(matrix, dt_s * drive - (matrix - np.diag(c)) @ old_x)
        except (np.linalg.LinAlgError, FloatingPointError) as error:
            raise ThermalError("SOLVER_FAILED", str(error), ValidityStatus.MODEL_INVALID) from error
        require(
            np.all(np.isfinite(nx)),
            "SOLVER_FAILED",
            "nonfinite state",
            ValidityStatus.MODEL_INVALID,
        )
        new_t = nx + anchor
        next_solids = tuple(n.at_temperature(new_t[index[n.node_id]]) for n in state.solids)
        pressures = dict(hydraulic.pressures_pa)
        pressure_map = dict(plant.volume_pressure_nodes)
        next_volumes = tuple(
            replace(
                v.at_temperature(new_t[index[v.volume_id]]),
                pressure_pa=plant.pressure_reference_pa.value
                + pressures[pressure_map[v.volume_id]],
            )
            for v in state.volumes
        )
        next_state = PlantState(next_solids, next_volumes, state.time_ns + dt_ns)
        hx = evaluate(
            plant.heat_exchanger,
            secondary_flow,
            primary_flow,
            next_state.by_id[plant.cdu_volume_id].temperature_k,
            fws_t,
        )
        thermal_flux = []
        air_j = 0.0
        for edge in plant.interfaces:
            i = index[edge.hot_node_id]
            g, flow = edge_conductance[edge.interface_id]
            j = index.get(edge.cold_node_id)
            cold_t = new_t[j] if j is not None else ambient_t
            edge.conductance(new_t[i], cold_t, flow)
            energy = float(dt_s * g * (new_t[i] - cold_t))
            thermal_flux.append((edge.interface_id, edge.hot_node_id, edge.cold_node_id, energy))
            if j is None:
                air_j += energy
        advective = tuple(
            AdvectiveEnergy(
                l.link_id,
                l.donor_id,
                l.receiver_id,
                l.magnitude * dt_s,
                l.magnitude * dt_s * next_state.by_id[l.donor_id].specific_enthalpy_j_kg,
                l.owner_id,
            )
            for l in links
        )
        hx_j = hx.secondary_out_w * dt_s
        stored = fsum(
            new.energy_j - old.energy_j
            for old, new in zip(
                (*state.solids, *state.volumes), (*next_state.solids, *next_state.volumes)
            )
        )
        source_j = fsum(r.energy_j for r in receipts)
        pump_heat_w = pump.loss_to_liquid_w + fsum(d.liquid_w for d in hydraulic.dissipations)
        pump_ambient_w = pump.loss_to_ambient_w + fsum(d.ambient_w for d in hydraulic.dissipations)
        residual = stored - (source_j + pump_heat_w * dt_s - air_j - hx_j)
        scale = abs(stored) + abs(source_j) + abs(pump_heat_w * dt_s) + abs(air_j) + abs(hx_j)
        require(
            abs(residual) <= 1e-6 + 1e-6 * scale,
            "ENERGY_BALANCE_FAIL",
            "full secondary loop",
            ValidityStatus.MODEL_INVALID,
        )
        node_residuals, node_scales = [], []
        for name in ids:
            old, new = by_id[name], next_state.by_id[name]
            src = fsum(r.energy_j for r in receipts if r.thermal_node_id == name)
            src += dt_s * heat_receiver.get(name, 0.0)
            conduction = fsum(
                e if cold == name else -e if hot == name and cold is not None else 0.0
                for _, hot, cold, e in thermal_flux
            )
            transport = fsum(
                t.energy_j if t.receiver_id == name else -t.energy_j if t.donor_id == name else 0.0
                for t in advective
            )
            external = fsum(
                e for _, hot, cold, e in thermal_flux if hot == name and cold is None
            ) + (hx_j if name == plant.cdu_volume_id else 0.0)
            node_residual = new.energy_j - old.energy_j - (src + conduction + transport - external)
            node_scale = abs(new.energy_j - old.energy_j) + abs(src) + abs(conduction)
            node_scale += abs(transport) + abs(external)
            require(
                abs(node_residual) <= 1e-6 + 1e-6 * node_scale,
                "ENERGY_BALANCE_FAIL",
                name,
                ValidityStatus.MODEL_INVALID,
            )
            node_residuals.append((name, node_residual))
            node_scales.append((name, node_scale))
        max_mass_interval = max(abs(v) * dt_s for v in mass.values())
        require(
            all(
                abs(mass[name]) * dt_s <= 1e-9 + 1e-8 * mass_incident[name] * dt_s for name in mass
            ),
            "MASS_BALANCE_FAIL",
            "volume interval",
            ValidityStatus.MODEL_INVALID,
        )
        require(
            abs(fsum(d.total_w for d in hydraulic.dissipations) - pump.hydraulic_w)
            <= max(1e-6, 1e-9 * pump.hydraulic_w),
            "PUMP_ENERGY_BALANCE_FAIL",
            "passive dissipation",
            ValidityStatus.MODEL_INVALID,
        )
        ledger = PlantEnergyLedger(
            source_j,
            stored,
            air_j,
            hx_j,
            pump.electrical_energy_j,
            pump.hydraulic_w * dt_s,
            pump_heat_w * dt_s,
            pump_ambient_w * dt_s,
            residual,
            tuple(node_residuals),
            tuple(node_scales),
            tuple(mass.items()),
            tuple(mass_incident.items()),
            tuple((eid, e) for eid, _, _, e in thermal_flux),
            advective,
            hydraulic.max_mass_residual_kg_s,
            max_mass_interval / dt_s,
        )
        return PlantStep(
            next_state,
            hydraulic,
            pump,
            hx,
            ledger,
            SolverStatus.CONVERGED,
            ValidityStatus.VALID,
            (),
            tuple(coldplate_uses),
        )
    except ThermalError as error:
        return PlantStep(
            state, None, None, None, None, SolverStatus.FAILED, error.status, (str(error),)
        )
