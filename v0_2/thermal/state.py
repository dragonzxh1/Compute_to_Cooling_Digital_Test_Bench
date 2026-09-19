from dataclasses import dataclass

from .nodes import ThermalNodeState
from .validity import require


@dataclass(frozen=True)
class ThermalState:
    nodes: tuple[ThermalNodeState, ...]
    time_ns: int = 0

    def __post_init__(self):
        require(type(self.nodes) is tuple and bool(self.nodes), "STATE", "nonempty immutable nodes")
        require(type(self.time_ns) is int and self.time_ns >= 0, "INVALID_TIME", "state time")
        for key in ("node_id", "storage_owner_id"):
            values = [getattr(n, key) for n in self.nodes]
            require(len(set(values)) == len(values), "DUPLICATE_STORAGE_OR_NODE", key)

    def by_id(self):
        return {n.node_id: n for n in self.nodes}
