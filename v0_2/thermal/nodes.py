from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from .provenance import ParameterRecord
from .validity import ValidityStatus, finite, require


class NodeType(StrEnum):
    GPU_DIE = "GPU_DIE"
    GPU_PACKAGE = "GPU_PACKAGE"
    HBM = "HBM"
    VRM_BOARD = "VRM_BOARD"
    CPU_DIE = "CPU_DIE"
    CPU_PACKAGE = "CPU_PACKAGE"
    COLD_PLATE = "COLD_PLATE"
    LOCAL_COOLANT = "LOCAL_COOLANT"
    RACK_AIR = "RACK_AIR"


class EnthalpyLaw(Protocol):
    """Future variable-C law must integrate C(T), with a consistent inverse."""

    def energy(self, temperature_k: float, reference_k: float) -> float: ...
    def temperature(self, energy_j: float, reference_k: float) -> float: ...


@dataclass(frozen=True)
class ConstantCapacity:
    capacitance: ParameterRecord

    def __post_init__(self):
        require(self.capacitance.si("J/K") > 0, "INVALID_CAPACITY", "C must be positive")

    def energy(self, temperature_k, reference_k):
        return self.capacitance.value * (temperature_k - reference_k)

    def temperature(self, energy_j, reference_k):
        return reference_k + energy_j / self.capacitance.value


@dataclass(frozen=True)
class ThermalNodeState:
    node_id: str
    entity_id: str
    node_type: NodeType
    temperature_k: float
    energy_j: float
    thermal_capacitance: ParameterRecord
    reference_temperature_k: float
    storage_owner_id: str
    valid_temperature_range: tuple[float, float]
    provenance: ParameterRecord
    calibration_status: str
    mass_kg: ParameterRecord | None = None
    specific_heat: ParameterRecord | None = None
    coolant: str | None = None
    adiabatic: bool = False

    def __post_init__(self):
        require(
            bool(self.node_id and self.entity_id and self.storage_owner_id), "NODE_ID", "empty ID"
        )
        require(isinstance(self.node_type, NodeType), "NODE_TYPE", self.node_id)
        for value in (self.temperature_k, self.energy_j, self.reference_temperature_k):
            finite(value, self.node_id)
        require(
            type(self.valid_temperature_range) is tuple and len(self.valid_temperature_range) == 2,
            "INVALID_RANGE",
            self.node_id,
        )
        lo, hi = self.valid_temperature_range
        finite(lo, "temperature_min")
        finite(hi, "temperature_max")
        require(0 < lo < hi and self.reference_temperature_k >= 0, "INVALID_RANGE", self.node_id)
        require(
            lo <= self.temperature_k <= hi,
            "TEMPERATURE_OUT_OF_RANGE",
            self.node_id,
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        law = self.enthalpy_law
        require(
            abs(law.energy(self.temperature_k, self.reference_temperature_k) - self.energy_j)
            <= 1e-8,
            "INCONSISTENT_ENERGY",
            self.node_id,
        )
        require(
            self.calibration_status == self.thermal_capacitance.calibration_status,
            "PROVENANCE",
            "storage calibration cannot be promoted",
        )
        if self.node_type == NodeType.LOCAL_COOLANT:
            require(
                self.mass_kg is not None and self.specific_heat is not None and bool(self.coolant),
                "COOLANT_STORAGE",
                self.node_id,
            )
            m, cp = self.mass_kg.si("kg"), self.specific_heat.si("J/(kg*K)")
            require(
                m > 0
                and cp > 0
                and abs(m * cp - self.thermal_capacitance.value) <= max(1e-9, 1e-12 * m * cp),
                "COOLANT_STORAGE",
                "C != mass*cp",
            )

    @property
    def enthalpy_law(self) -> EnthalpyLaw:
        return ConstantCapacity(self.thermal_capacitance)

    def at_temperature(self, value):
        return replace(
            self,
            temperature_k=float(value),
            energy_j=self.enthalpy_law.energy(float(value), self.reference_temperature_k),
        )
