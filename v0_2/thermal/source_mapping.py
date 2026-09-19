from dataclasses import dataclass
from math import fsum

from .nodes import NodeType
from .provenance import ParameterRecord
from .validity import finite, interval, require


def power_tolerance(power):
    return max(1e-6, 1e-9 * abs(power))


@dataclass(frozen=True)
class PowerLeaf:
    source_id: str
    component_kind: str
    power: ParameterRecord
    component_ids: frozenset[str]
    included_in: tuple[str, ...] = ()
    value_origin: str = "ENGINEERING_ASSUMPTION"
    sample_time_ns: int = 0

    def __post_init__(self):
        require(
            bool(self.source_id)
            and type(self.component_ids) is frozenset
            and bool(self.component_ids)
            and all(self.component_ids),
            "POWER_DOMAIN",
            "missing immutable coverage",
        )
        require(
            self.component_kind in NodeType.__members__ or self.component_kind == "BOARD_POWER",
            "POWER_DOMAIN",
            "unrecognized component kind",
        )
        require(
            type(self.included_in) is tuple and self.source_id not in self.included_in,
            "POWER_DOMAIN",
            "cyclic coverage",
        )
        require(self.power.si("W") >= 0, "POWER_DOMAIN", "negative electrical power")
        require(
            type(self.sample_time_ns) is int and self.sample_time_ns >= 0,
            "POWER_DOMAIN",
            "sample time",
        )
        require(
            self.value_origin
            in {
                "MEASURED_DIRECT",
                "ALLOCATED_FROM_PARENT",
                "ENGINEERING_ASSUMPTION",
                "CALIBRATED_ESTIMATE",
            },
            "POWER_DOMAIN",
            "origin",
        )


@dataclass(frozen=True)
class ThermalSourceReceipt:
    source_id: str
    thermal_node_id: str
    power_w: float
    start_ns: int
    end_ns: int
    energy_j: float


@dataclass(frozen=True)
class PowerSourceMap:
    assignments: tuple[tuple[str, str], ...]

    def validate(self, leaves, nodes):
        require(type(self.assignments) is tuple, "SOURCE_MAP", "immutable assignments")
        ids = [leaf.source_id for leaf in leaves]
        assigned = [source for source, _ in self.assignments]
        require(
            len(set(ids)) == len(ids) and len(set(assigned)) == len(assigned),
            "DUPLICATE_SOURCE_RECEIPT",
            "each electrical leaf once",
        )
        require(set(assigned) == set(ids), "INCOMPLETE_SOURCE_MAP", "missing or extra leaf")
        covered = set()
        mapping = dict(self.assignments)
        for leaf in leaves:
            require(
                not (set(leaf.included_in) & set(ids)),
                "POWER_DOMAIN_OVERLAP",
                "parent and child both accepted",
            )
            require(not (covered & leaf.component_ids), "POWER_DOMAIN_OVERLAP", leaf.source_id)
            covered.update(leaf.component_ids)
            require(
                leaf.component_kind != "BOARD_POWER",
                "BOARD_REQUIRES_ALLOCATION",
                "board power cannot be injected as die power",
            )
            target = mapping[leaf.source_id]
            require(target in nodes, "SOURCE_ENDPOINT", target)
            require(
                nodes[target].node_type.value == leaf.component_kind,
                "SOURCE_DOMAIN_MISMATCH",
                leaf.source_id,
            )

    def receipts(self, leaves, nodes, t_ns, dt_ns):
        interval(t_ns, dt_ns)
        self.validate(leaves, nodes)
        mapping = dict(self.assignments)
        require(
            all(leaf.sample_time_ns <= t_ns for leaf in leaves),
            "FUTURE_SOURCE",
            "source is not active yet",
        )
        result = tuple(
            ThermalSourceReceipt(
                leaf.source_id,
                mapping[leaf.source_id],
                leaf.power.value,
                t_ns,
                t_ns + dt_ns,
                leaf.power.value * dt_ns / 1e9,
            )
            for leaf in leaves
        )
        total = fsum(leaf.power.value for leaf in leaves)
        require(
            abs(fsum(r.energy_j for r in result) - total * dt_ns / 1e9)
            <= power_tolerance(total) * dt_ns / 1e9,
            "POWER_DOMAIN_BALANCE_FAIL",
            "receipt J",
        )
        return result


def allocate_parent(parent, known_children, residual_specs):
    """One parent budget; specs are (id, kind, component_ids, fraction ParameterRecord)."""
    require(parent.component_kind == "BOARD_POWER", "POWER_DOMAIN", "expected board budget")
    known_children = tuple(known_children)
    residual_specs = tuple(residual_specs)
    require(bool(residual_specs), "POWER_DOMAIN_BALANCE_FAIL", "residual partition required")
    residual = parent.power.value - fsum(c.power.value for c in known_children)
    require(residual >= 0, "POWER_DOMAIN_BALANCE_FAIL", "children exceed parent; no clipping")
    seen, ids = set(), set()
    for child in known_children:
        require(
            parent.source_id in child.included_in and child.sample_time_ns == parent.sample_time_ns,
            "POWER_DOMAIN_BALANCE_FAIL",
            "coverage/time mismatch",
        )
        require(
            not (seen & child.component_ids) and child.source_id not in ids,
            "POWER_DOMAIN_OVERLAP",
            child.source_id,
        )
        seen.update(child.component_ids)
        ids.add(child.source_id)
    weights = []
    for source, kind, components, weight in residual_specs:
        w = weight.si("fraction")
        finite(w, "allocation fraction")
        require(
            0 <= w <= 1 and source not in ids and not (seen & set(components)),
            "POWER_DOMAIN_OVERLAP",
            source,
        )
        require(bool(components), "POWER_DOMAIN", "empty component set")
        weights.append(w)
        seen.update(components)
        ids.add(source)
    require(
        seen == set(parent.component_ids) and abs(fsum(weights) - 1) <= 1e-12,
        "POWER_DOMAIN_BALANCE_FAIL",
        "coverage/fractions",
    )
    allocated = []
    for (source, kind, components, weight), w in zip(residual_specs, weights):
        p = ParameterRecord(
            source,
            residual * w,
            "W",
            "ENGINEERING_ASSUMPTION",
            f"parent:{parent.source_id}; allocation:{weight.source_ref}",
            min(parent.power.confidence, weight.confidence),
            weight.date,
            (0, parent.power.value),
            "CALIBRATION_REQUIRED",
        )
        allocated.append(
            PowerLeaf(
                source,
                kind,
                p,
                frozenset(components),
                (parent.source_id, *parent.included_in),
                "ALLOCATED_FROM_PARENT",
                parent.sample_time_ns,
            )
        )
    result = (*known_children, *allocated)
    require(
        abs(fsum(c.power.value for c in result) - parent.power.value)
        <= power_tolerance(parent.power.value),
        "POWER_DOMAIN_BALANCE_FAIL",
        "parent budget",
    )
    return result
