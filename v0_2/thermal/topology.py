from dataclasses import dataclass

from .coldplate import GenericColdplate, ManufacturerColdplateSchema, canonical_layer
from .interfaces import ThermalInterface
from .nodes import NodeType
from .state import ThermalState
from .validity import require


@dataclass(frozen=True)
class ThermalTopology:
    initial_state: ThermalState
    interfaces: tuple[ThermalInterface, ...]
    device_cvs: tuple[tuple[str, tuple[str, ...]], ...]

    def __post_init__(self):
        require(
            type(self.interfaces) is tuple and type(self.device_cvs) is tuple,
            "TOPOLOGY",
            "immutable configuration",
        )
        nodes = self.initial_state.by_id()
        ids, owners, layers, connected = set(), set(), set(), set()
        for edge in self.interfaces:
            require(
                edge.interface_id not in ids and edge.owner_id not in owners,
                "DUPLICATE_INTERFACE_OWNER",
                edge.interface_id,
            )
            ids.add(edge.interface_id)
            owners.add(edge.owner_id)
            require(
                edge.hot_node_id in nodes
                and (edge.cold_node_id is None or edge.cold_node_id in nodes),
                "MISSING_ENDPOINT",
                edge.interface_id,
            )
            require(edge.hot_node_id != edge.cold_node_id, "SELF_INTERFACE", edge.interface_id)
            require(
                edge.external_boundary_id not in nodes,
                "BOUNDARY_STORAGE_CONFLICT",
                edge.interface_id,
            )
            connected.add(edge.hot_node_id)
            if edge.cold_node_id:
                connected.add(edge.cold_node_id)
            for layer in edge.included_layer_ids:
                layer = canonical_layer(layer)
                require(layer not in layers, "THERMAL_RESISTANCE_OVERLAP", layer)
                require(":" in layer, "LAYER_ID", "expected instance:physical_layer")
                layers.add(layer)
        # Check overlap before imported endpoint/type checks, so conflicts cannot be hidden.
        for edge in self.interfaces:
            if isinstance(edge.resistance_model, (GenericColdplate, ManufacturerColdplateSchema)):
                model, d = edge.resistance_model, edge.resistance_model.definition
                require(
                    tuple(edge.included_layer_ids) == d.included_layers
                    and edge.hot_node_id == d.thermal_hot_endpoint_id
                    and edge.cold_node_id == d.thermal_cold_endpoint_id,
                    "IMPORT_CONFLICT",
                    edge.interface_id,
                )
                if isinstance(model, GenericColdplate):
                    require(
                        nodes[edge.hot_node_id].node_type == NodeType.COLD_PLATE
                        and nodes[edge.cold_node_id].node_type == NodeType.LOCAL_COOLANT,
                        "IMPORT_CONFLICT",
                        "Generic endpoints must be plate->bulk",
                    )
                    require(
                        nodes[edge.cold_node_id].coolant == model.coolant,
                        "COOLANT_MISMATCH",
                        "node vs model",
                    )
        for node in nodes.values():
            require(
                node.node_id in connected or node.adiabatic, "UNDECLARED_ADIABATIC", node.node_id
            )
        cv_ids = set()
        for cv, members in self.device_cvs:
            require(
                cv
                and cv not in cv_ids
                and cv != "subsystem"
                and not cv.startswith("node:")
                and type(members) is tuple
                and members
                and len(set(members)) == len(members)
                and set(members) <= set(nodes),
                "ENERGY_TOPOLOGY_FAIL",
                cv,
            )
            cv_ids.add(cv)

    def validate_state(self, state):
        require(
            tuple(n.node_id for n in state.nodes)
            == tuple(n.node_id for n in self.initial_state.nodes),
            "STATE_TOPOLOGY",
            "node order",
        )
        for original, current in zip(self.initial_state.nodes, state.nodes):
            require(
                original.at_temperature(current.temperature_k) == current,
                "STATE_TOPOLOGY",
                "immutable node properties changed",
            )
