from dataclasses import dataclass
from math import fsum, sqrt

from v0_2.hydraulics.graph import HydraulicGraph
from v0_2.hydraulics.pump import PumpCurve
from v0_2.thermal.validity import ThermalError, ValidityStatus, require


@dataclass(frozen=True)
class DissipationRecord:
    edge_id: str
    receiver_id: str
    total_w: float
    liquid_w: float
    ambient_w: float


@dataclass(frozen=True)
class HydraulicSolution:
    total_flow_m3_s: float
    branch_flows_m3_s: tuple[float, ...]
    pump_head_pa: float
    manifold_dp_pa: float
    pressures_pa: tuple[tuple[str, float], ...]
    edge_flows_m3_s: tuple[tuple[str, float], ...]
    edge_drops_pa: tuple[tuple[str, float], ...]
    dissipations: tuple[DissipationRecord, ...]
    node_mass_residual_kg_s: tuple[tuple[str, float], ...]
    node_mass_incident_kg_s: tuple[tuple[str, float], ...]
    iterations: int
    residual_norm: float
    max_mass_residual_kg_s: float
    max_pressure_residual_pa: float
    pump_curve_residual_pa: float


def solve(graph: HydraulicGraph, curve: PumpCurve, speed_actual: float, density_kg_m3: float):
    """Exact common-manifold solution for quadratic paths, with a full-node audit."""
    require(density_kg_m3 > 0, "FLUID_PROPERTY", "density")
    branch_k = [fsum(e.coefficient.value for e in path) for path in graph.branches]
    require(all(k > 0 for k in branch_k), "SOLVER_FAILED", "nonpositive branch K")
    admittance = fsum(1 / sqrt(k) for k in branch_k)
    equivalent_k = 1 / admittance**2
    series_k = fsum(e.coefficient.value for e in (*graph.supply_series, *graph.return_series))
    denominator = series_k + equivalent_k + curve.curve_k.value
    require(denominator > 0, "SOLVER_FAILED", "no intersection", ValidityStatus.MODEL_INVALID)
    try:
        curve.head(0.0, speed_actual)
        total = sqrt(curve.shutoff_head_pa.value * speed_actual**2 / denominator)
        pump_dp = curve.head(total, speed_actual)
        manifold_dp = equivalent_k * total**2
        branches = tuple(sqrt(manifold_dp / k) for k in branch_k)
        pressure = {graph.return_node: 0.0, graph.pump_outlet_node: pump_dp}
        edge_flows = {graph.pump_edge_id: total}
        drops = {}
        dissipations = []

        def walk(path, q, start):
            current = start
            for edge in path:
                dp = edge.drop_pa(q)
                pressure[edge.to_node] = current - dp
                current -= dp
                edge_flows[edge.edge_id] = q
                drops[edge.edge_id] = dp
                watts = dp * q
                fraction = edge.liquid_fraction.value
                dissipations.append(
                    DissipationRecord(
                        edge.edge_id,
                        edge.receiver_id,
                        watts,
                        watts * fraction,
                        watts * (1 - fraction),
                    )
                )
            return current

        supply = walk(graph.supply_series, total, pump_dp)
        # Supply manifold absolute gauge pressure is set by the return path.
        return_pressure = fsum(e.coefficient.value for e in graph.return_series) * total**2
        pressure[graph.supply_manifold] = supply
        pressure[graph.return_manifold] = return_pressure
        branch_errors = []
        for path, q in zip(graph.branches, branches):
            branch_errors.append(abs(walk(path, q, supply) - return_pressure))
        end_pressure = walk(graph.return_series, total, return_pressure)
        edges_by_id = {e.edge_id: e for e in graph.passive_edges}
        mass = {n.node_id: 0.0 for n in graph.nodes}
        incident = {n.node_id: 0.0 for n in graph.nodes}
        for edge_id, q in edge_flows.items():
            if edge_id == graph.pump_edge_id:
                source, target = graph.return_node, graph.pump_outlet_node
            else:
                edge = edges_by_id[edge_id]
                source, target = edge.from_node, edge.to_node
            m = q * density_kg_m3
            mass[source] -= m
            mass[target] += m
            incident[source] += abs(m)
            incident[target] += abs(m)
        max_mass = max(abs(v) for v in mass.values())
        for name, value in mass.items():
            require(
                abs(value) <= 1e-9 + 1e-8 * incident[name],
                "MASS_BALANCE_FAIL",
                name,
                ValidityStatus.MODEL_INVALID,
            )
        pump_residual = abs(pump_dp - (series_k * total**2 + manifold_dp))
        pressure_residual = max(abs(end_pressure), *branch_errors)
        hydraulic_residual = abs(fsum(r.total_w for r in dissipations) - pump_dp * total)
        norm = max(pump_residual, pressure_residual, hydraulic_residual)
        require(
            pump_residual <= 1e-6 + 1e-9 * pump_dp
            and pressure_residual <= 1e-6 + 1e-9 * pump_dp
            and hydraulic_residual <= max(1e-6, 1e-9 * pump_dp * total),
            "SOLVER_FAILED",
            f"pressure/energy residual={norm}",
            ValidityStatus.MODEL_INVALID,
        )
        return HydraulicSolution(
            total,
            branches,
            pump_dp,
            manifold_dp,
            tuple(pressure.items()),
            tuple(edge_flows.items()),
            tuple(drops.items()),
            tuple(dissipations),
            tuple(mass.items()),
            tuple(incident.items()),
            1,
            norm,
            max_mass,
            pressure_residual,
            pump_residual,
        )
    except (OverflowError, ZeroDivisionError) as error:
        raise ThermalError("SOLVER_FAILED", str(error), ValidityStatus.MODEL_INVALID) from error
