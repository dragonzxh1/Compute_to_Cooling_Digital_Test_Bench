from dataclasses import dataclass
from enum import StrEnum

from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import ValidityStatus, finite, require


class EdgeKind(StrEnum):
    PIPE = "PIPE"
    MANIFOLD_CONNECTION = "MANIFOLD_CONNECTION"
    GENERIC_RESISTANCE = "GENERIC_RESISTANCE"
    COLDPLATE_RESISTANCE = "COLDPLATE_RESISTANCE"
    VALVE = "VALVE"


@dataclass(frozen=True)
class PressureNode:
    node_id: str
    loop_id: str


@dataclass(frozen=True)
class HydraulicEdge:
    edge_id: str
    from_node: str
    to_node: str
    kind: EdgeKind
    coefficient: ParameterRecord
    valid_q_m3_s: tuple[float, float]
    receiver_id: str
    liquid_fraction: ParameterRecord
    provenance: ParameterRecord
    reverse_supported: bool = False

    def __post_init__(self):
        require(bool(self.edge_id and self.from_node and self.to_node), "HYDRAULIC_EDGE", "ID")
        require(self.from_node != self.to_node, "HYDRAULIC_EDGE", "self edge")
        require(isinstance(self.kind, EdgeKind), "HYDRAULIC_EDGE", "kind")
        require(self.coefficient.si("Pa/(m3/s)^2") > 0, "INVALID_K", self.edge_id)
        require(
            type(self.valid_q_m3_s) is tuple
            and len(self.valid_q_m3_s) == 2
            and 0 <= self.valid_q_m3_s[0] < self.valid_q_m3_s[1],
            "INVALID_RANGE",
            self.edge_id,
        )
        require(
            0 <= self.liquid_fraction.si("fraction") <= 1,
            "LOSS_DESTINATION",
            self.edge_id,
        )
        require(bool(self.receiver_id), "LOSS_DESTINATION", self.edge_id)

    def drop_pa(self, flow_m3_s):
        finite(flow_m3_s, "volumetric flow")
        require(
            flow_m3_s >= 0 or self.reverse_supported,
            "REVERSE_FLOW",
            self.edge_id,
            ValidityStatus.MODEL_INVALID,
        )
        require(
            self.valid_q_m3_s[0] <= abs(flow_m3_s) <= self.valid_q_m3_s[1],
            "FLOW_OUT_OF_RANGE",
            self.edge_id,
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        return self.coefficient.value * flow_m3_s * abs(flow_m3_s)


def _check_path(path, first, last, seen):
    require(bool(path), "HYDRAULIC_GRAPH", "empty path")
    current = first
    for edge in path:
        require(edge.edge_id not in seen, "HYDRAULIC_GRAPH", "duplicate edge")
        require(edge.from_node == current, "HYDRAULIC_GRAPH", edge.edge_id)
        seen.add(edge.edge_id)
        current = edge.to_node
    require(current == last, "HYDRAULIC_GRAPH", f"path must end at {last}")


@dataclass(frozen=True)
class HydraulicGraph:
    nodes: tuple[PressureNode, ...]
    return_node: str
    pump_outlet_node: str
    supply_manifold: str
    return_manifold: str
    supply_series: tuple[HydraulicEdge, ...]
    branches: tuple[tuple[HydraulicEdge, ...], ...]
    return_series: tuple[HydraulicEdge, ...]
    pump_edge_id: str

    def __post_init__(self):
        ids = [n.node_id for n in self.nodes]
        require(len(set(ids)) == len(ids) and bool(ids), "HYDRAULIC_GRAPH", "node IDs")
        require(len({n.loop_id for n in self.nodes}) == 1, "PRIMARY_SECONDARY_MIX", "node loop")
        require(
            all(
                x in ids
                for x in (
                    self.return_node,
                    self.pump_outlet_node,
                    self.supply_manifold,
                    self.return_manifold,
                )
            ),
            "HYDRAULIC_GRAPH",
            "missing pressure node",
        )
        require(self.pump_edge_id and self.pump_edge_id not in ids, "HYDRAULIC_GRAPH", "pump ID")
        require(bool(self.branches), "HYDRAULIC_GRAPH", "no branches")
        seen = {self.pump_edge_id}
        _check_path(self.supply_series, self.pump_outlet_node, self.supply_manifold, seen)
        for branch in self.branches:
            _check_path(branch, self.supply_manifold, self.return_manifold, seen)
        _check_path(self.return_series, self.return_manifold, self.return_node, seen)
        require(
            all(
                e.from_node in ids and e.to_node in ids
                for path in (self.supply_series, *self.branches, self.return_series)
                for e in path
            ),
            "HYDRAULIC_GRAPH",
            "unknown edge endpoint",
        )
        connected = {self.return_node, self.pump_outlet_node}
        for path in (self.supply_series, *self.branches, self.return_series):
            for edge in path:
                connected.update((edge.from_node, edge.to_node))
        require(set(ids) == connected, "HYDRAULIC_GRAPH", "orphan pressure node")

    @property
    def passive_edges(self):
        return (
            *self.supply_series,
            *(edge for path in self.branches for edge in path),
            *self.return_series,
        )
