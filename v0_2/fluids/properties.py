from dataclasses import dataclass
from typing import Protocol

from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import ValidityStatus, finite, require


class EnthalpyProperties(Protocol):
    fluid_id: str

    def h(self, temperature_k: float) -> float: ...

    def temperature(self, specific_enthalpy_j_kg: float) -> float: ...


@dataclass(frozen=True)
class ConstantCpFluid:
    fluid_id: str
    density: ParameterRecord
    specific_heat: ParameterRecord
    reference_temperature: ParameterRecord
    valid_temperature_k: tuple[float, float]
    provenance: ParameterRecord

    def __post_init__(self):
        require(bool(self.fluid_id), "FLUID_ID", "empty")
        require(self.density.si("kg/m3") > 0, "FLUID_PROPERTY", "density")
        require(self.specific_heat.si("J/(kg*K)") > 0, "FLUID_PROPERTY", "Cp")
        self.reference_temperature.si("K")
        require(
            type(self.valid_temperature_k) is tuple
            and len(self.valid_temperature_k) == 2
            and 0 < self.valid_temperature_k[0] < self.valid_temperature_k[1],
            "FLUID_PROPERTY",
            "temperature range",
        )

    def h(self, temperature_k):
        finite(temperature_k, "fluid T")
        require(
            self.valid_temperature_k[0] <= temperature_k <= self.valid_temperature_k[1],
            "FLUID_T_OUT_OF_RANGE",
            str(temperature_k),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
        return self.specific_heat.value * (temperature_k - self.reference_temperature.value)

    def temperature(self, specific_enthalpy_j_kg):
        finite(specific_enthalpy_j_kg, "specific enthalpy")
        t = self.reference_temperature.value + specific_enthalpy_j_kg / self.specific_heat.value
        self.h(t)
        return t
