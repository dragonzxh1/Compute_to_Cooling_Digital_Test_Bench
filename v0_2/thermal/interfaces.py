from dataclasses import dataclass
from enum import StrEnum

from .coldplate import GenericColdplate, ManufacturerColdplateSchema
from .provenance import ParameterRecord
from .validity import ValidityStatus, require


class InterfaceKind(StrEnum):
    CONDUCTIVE_RESISTANCE = "CONDUCTIVE_RESISTANCE"
    CONVECTIVE_RESISTANCE = "CONVECTIVE_RESISTANCE"
    COLDPLATE_FLOW_DEPENDENT = "COLDPLATE_FLOW_DEPENDENT"
    PRESCRIBED_BOUNDARY = "PRESCRIBED_BOUNDARY"


@dataclass(frozen=True)
class ThermalInterface:
    interface_id: str
    hot_node_id: str
    cold_node_id: str | None
    external_boundary_id: str | None
    resistance_model: ParameterRecord | GenericColdplate | ManufacturerColdplateSchema
    included_layer_ids: tuple[str, ...]
    owner_id: str
    kind: InterfaceKind
    provenance: ParameterRecord
    validity: ValidityStatus = ValidityStatus.VALID
    boundary_medium: str | None = None

    def __post_init__(self):
        require(bool(self.interface_id and self.hot_node_id and self.owner_id), "INTERFACE", "ID")
        require(
            (self.cold_node_id is None) != (self.external_boundary_id is None),
            "INTERFACE",
            "exactly one cold endpoint",
        )
        require(
            type(self.included_layer_ids) is tuple
            and bool(self.included_layer_ids)
            and all(self.included_layer_ids),
            "INTERFACE",
            "immutable layer IDs required",
        )
        require(
            isinstance(self.kind, InterfaceKind) and self.validity == ValidityStatus.VALID,
            "INTERFACE",
            "invalid constitutive interface",
        )
        if isinstance(self.resistance_model, ParameterRecord):
            require(self.resistance_model.si("K/W") > 0, "INVALID_RESISTANCE", self.interface_id)
            require(
                self.kind != InterfaceKind.COLDPLATE_FLOW_DEPENDENT,
                "INTERFACE",
                "coldplate model required",
            )
        else:
            require(
                isinstance(self.resistance_model, (GenericColdplate, ManufacturerColdplateSchema))
                and self.kind == InterfaceKind.COLDPLATE_FLOW_DEPENDENT,
                "INTERFACE",
                "unsupported resistance model",
            )
        if self.external_boundary_id is not None:
            require(
                self.kind == InterfaceKind.PRESCRIBED_BOUNDARY
                and self.boundary_medium in {"AIR", "LIQUID", "OTHER"},
                "INTERFACE",
                "external boundary classification",
            )
        else:
            require(
                self.kind != InterfaceKind.PRESCRIBED_BOUNDARY and self.boundary_medium is None,
                "INTERFACE",
                "internal exchange cannot also be counted as external heat",
            )

    def conductance(self, hot_k, cold_k, flow=None):
        model = self.resistance_model
        if isinstance(model, GenericColdplate):
            return 1 / model.evaluate(hot_k, cold_k, flow).endpoint_resistance_k_w
        require(
            not isinstance(model, ManufacturerColdplateSchema),
            "IMPORT_SCHEMA_ONLY",
            "Phase 3 manufacturer schema is not an executable curve",
            ValidityStatus.MODEL_INVALID,
        )
        return 1 / model.value
