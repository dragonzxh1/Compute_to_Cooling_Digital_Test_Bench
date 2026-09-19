from dataclasses import dataclass
from enum import StrEnum

from .provenance import ParameterRecord
from .validity import ValidityStatus, finite, require


class ZeroFlowPolicy(StrEnum):
    MODEL_INVALID = "MODEL_INVALID"
    ZERO_FLOW_VALID_MODEL = "ZERO_FLOW_VALID_MODEL"


def canonical_layer(layer):
    """Normalize equivalent contract/example names without changing the instance identity."""
    require(isinstance(layer, str) and ":" in layer, "LAYER_ID", "expected instance:physical_layer")
    instance, kind = layer.rsplit(":", 1)
    require(bool(instance) and bool(kind), "LAYER_ID", layer)
    kind = {
        "PLATE_INTERNAL_CONDUCTION": "PLATE_CONDUCTION",
        "PLATE_TO_COOLANT_CONVECTION": "PLATE_CONVECTION",
    }.get(kind, kind)
    return f"{instance}:{kind}"


@dataclass(frozen=True)
class ColdplateDefinition:
    thermal_hot_endpoint_id: str
    thermal_cold_endpoint_id: str
    hot_side_temperature_definition: str
    cold_side_temperature_definition: str
    rth_definition: str
    included_layers: tuple[str, ...]
    excluded_layers: tuple[str, ...]
    manufacturer_rth_definition: str = "NOT_APPLICABLE"
    manufacturer_measurement_hot_endpoint: str = "NOT_APPLICABLE"
    manufacturer_measurement_cold_endpoint: str = "NOT_APPLICABLE"

    def __post_init__(self):
        require(
            all(
                (
                    self.thermal_hot_endpoint_id,
                    self.thermal_cold_endpoint_id,
                    self.hot_side_temperature_definition,
                    self.cold_side_temperature_definition,
                    self.rth_definition,
                )
            ),
            "IMPORT_CONFLICT",
            "undefined endpoints",
        )
        require(
            type(self.included_layers) is tuple
            and type(self.excluded_layers) is tuple
            and bool(self.included_layers)
            and len(set(self.included_layers)) == len(self.included_layers)
            and not set(self.included_layers) & set(self.excluded_layers),
            "THERMAL_RESISTANCE_OVERLAP",
            "layer definition",
        )
        included = tuple(canonical_layer(layer) for layer in self.included_layers)
        excluded = tuple(canonical_layer(layer) for layer in self.excluded_layers)
        require(
            len(set(included)) == len(included) and not set(included) & set(excluded),
            "THERMAL_RESISTANCE_OVERLAP",
            "aliased physical layers",
        )
        require(
            self.thermal_hot_endpoint_id != self.thermal_cold_endpoint_id,
            "IMPORT_CONFLICT",
            "identical coldplate endpoints",
        )
        if self.manufacturer_rth_definition != "NOT_APPLICABLE":
            require(
                self.manufacturer_rth_definition == self.rth_definition
                and self.manufacturer_measurement_hot_endpoint == self.thermal_hot_endpoint_id
                and self.manufacturer_measurement_cold_endpoint == self.thermal_cold_endpoint_id,
                "IMPORT_CONFLICT",
                "manufacturer endpoint/definition mismatch",
            )


@dataclass(frozen=True)
class FlowInput:
    mass_flow: ParameterRecord
    coolant: str

    def __post_init__(self):
        self.mass_flow.si("kg/s")
        require(bool(self.coolant), "COOLANT_MISMATCH", "empty coolant identity")


@dataclass(frozen=True)
class ColdplateExchange:
    heat_transfer_w: float
    endpoint_resistance_k_w: float
    coolant_side_state: float
    validity_status: ValidityStatus = ValidityStatus.VALID


@dataclass(frozen=True)
class GenericColdplate:
    definition: ColdplateDefinition
    h_ref: ParameterRecord
    m_ref: ParameterRecord
    exponent: ParameterRecord
    conduction_r: ParameterRecord
    area: ParameterRecord
    flow_range: tuple[float, float]
    temperature_range: tuple[float, float]
    heat_load_range: tuple[float, float]
    coolant: str
    provenance: ParameterRecord
    zero_policy: ZeroFlowPolicy = ZeroFlowPolicy.MODEL_INVALID
    no_flow_resistance: ParameterRecord | None = None
    bidirectional: bool = False

    def __post_init__(self):
        for p, unit in (
            (self.h_ref, "W/(m2*K)"),
            (self.m_ref, "kg/s"),
            (self.conduction_r, "K/W"),
            (self.area, "m2"),
        ):
            require(p.si(unit) > 0, "COLDPLATE_PARAMETER", p.name)
        require(0 < self.exponent.si("fraction") <= 1, "COLDPLATE_PARAMETER", "exponent")
        for bounds, label in (
            (self.flow_range, "flow"),
            (self.temperature_range, "temperature"),
            (self.heat_load_range, "heat_load"),
        ):
            require(type(bounds) is tuple and len(bounds) == 2, "INVALID_RANGE", label)
            for value in bounds:
                finite(value, label)
            require(0 <= bounds[0] < bounds[1], "INVALID_RANGE", label)
        require(
            self.flow_range[0] > 0 and self.temperature_range[0] > 0,
            "INVALID_RANGE",
            "forced-flow range must exclude zero",
        )
        d = self.definition
        require(
            d.rth_definition == "COLDPLATE_SOLID_TO_LOCAL_BULK_COOLANT"
            and d.manufacturer_rth_definition == "NOT_APPLICABLE"
            and d.hot_side_temperature_definition == "REPRESENTATIVE_PLATE_SOLID"
            and d.cold_side_temperature_definition == "LOCAL_WELL_MIXED_BULK",
            "IMPORT_CONFLICT",
            "Generic endpoint definitions",
        )
        forbidden = {"DIE_PACKAGE", "PACKAGE_TIM", "TIM_CONTACT"}
        require(
            not any(layer.split(":")[-1] in forbidden for layer in d.included_layers),
            "THERMAL_RESISTANCE_OVERLAP",
            "Generic includes upstream layer",
        )
        require(
            {canonical_layer(layer).rsplit(":", 1)[1] for layer in d.included_layers}
            == {"PLATE_CONDUCTION", "PLATE_CONVECTION"},
            "IMPORT_CONFLICT",
            "Generic must own exactly plate conduction and plate-to-coolant convection",
        )
        require(isinstance(self.zero_policy, ZeroFlowPolicy), "ZERO_FLOW_POLICY", "unknown")
        if self.zero_policy == ZeroFlowPolicy.ZERO_FLOW_VALID_MODEL:
            require(
                self.no_flow_resistance is not None, "ZERO_FLOW_POLICY", "finite model required"
            )
            require(
                self.no_flow_resistance.si("K/W") >= self.conduction_r.value,
                "ZERO_FLOW_POLICY",
                "no-flow model below conduction bound",
            )
        else:
            require(self.no_flow_resistance is None, "ZERO_FLOW_POLICY", "inactive model")

    def resistance(self, flow):
        require(flow is not None, "MISSING_FLOW", "externally prescribed local flow required")
        require(
            flow.coolant == self.coolant,
            "COOLANT_MISMATCH",
            flow.coolant,
            ValidityStatus.MODEL_INVALID,
        )
        m = flow.mass_flow.si("kg/s")
        if m == 0:
            require(
                self.zero_policy == ZeroFlowPolicy.ZERO_FLOW_VALID_MODEL,
                "ZERO_FLOW",
                "no qualified finite model",
                ValidityStatus.MODEL_INVALID,
            )
            return self.no_flow_resistance.value
        require(
            m > 0 or self.bidirectional,
            "REVERSE_FLOW",
            "not qualified",
            ValidityStatus.MODEL_INVALID,
        )
        require(
            self.flow_range[0] <= abs(m) <= self.flow_range[1],
            "FLOW_OUT_OF_RANGE",
            str(m),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        h = self.h_ref.value * (abs(m) / self.m_ref.value) ** self.exponent.value
        r = self.conduction_r.value + 1 / (h * self.area.value)
        finite(r, "Rcp")
        return r

    def evaluate(self, hot_k, cold_k, flow):
        for t in (hot_k, cold_k):
            finite(t, "coldplate T")
            require(
                self.temperature_range[0] <= t <= self.temperature_range[1],
                "COLDPLATE_T_OUT_OF_RANGE",
                str(t),
                ValidityStatus.MODEL_OUT_OF_RANGE,
            )
        r = self.resistance(flow)
        q = (hot_k - cold_k) / r
        require(
            self.heat_load_range[0] <= abs(q) <= self.heat_load_range[1],
            "HEAT_LOAD_OUT_OF_RANGE",
            str(q),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        return ColdplateExchange(q, r, cold_k)


@dataclass(frozen=True)
class ManufacturerColdplateSchema:
    """Import validation only in Phase 3; no invented manufacturer curve evaluator."""

    definition: ColdplateDefinition
    provenance: ParameterRecord

    def __post_init__(self):
        require(
            self.definition.manufacturer_rth_definition != "NOT_APPLICABLE",
            "IMPORT_CONFLICT",
            "manufacturer definition missing",
        )
