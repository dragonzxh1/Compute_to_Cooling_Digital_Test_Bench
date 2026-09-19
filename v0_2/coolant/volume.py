from dataclasses import dataclass, replace

from v0_2.fluids.properties import ConstantCpFluid
from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import finite, require


@dataclass(frozen=True)
class CoolantVolumeState:
    volume_id: str
    mass_kg: ParameterRecord
    specific_enthalpy_j_kg: float
    temperature_k: float
    pressure_pa: float
    coolant_ref: str
    storage_owner_id: str
    fluid: ConstantCpFluid
    provenance: ParameterRecord

    def __post_init__(self):
        require(bool(self.volume_id and self.coolant_ref and self.storage_owner_id), "VOLUME", "ID")
        require(self.coolant_ref == self.fluid.fluid_id, "COOLANT_MISMATCH", self.volume_id)
        require(self.mass_kg.si("kg") > 0, "VOLUME", "positive mass")
        finite(self.pressure_pa, "pressure")
        require(self.pressure_pa >= 0, "VOLUME", "negative absolute pressure")
        finite(self.specific_enthalpy_j_kg, "h")
        require(
            abs(self.fluid.h(self.temperature_k) - self.specific_enthalpy_j_kg)
            <= max(1e-7, 1e-10 * abs(self.specific_enthalpy_j_kg)),
            "VOLUME_ENTHALPY_MISMATCH",
            self.volume_id,
        )

    @property
    def energy_j(self):
        return self.mass_kg.value * self.specific_enthalpy_j_kg

    def at_h(self, h):
        return replace(
            self, specific_enthalpy_j_kg=float(h), temperature_k=self.fluid.temperature(h)
        )

    def at_temperature(self, temperature_k):
        return self.at_h(self.fluid.h(temperature_k))

    def residence_time_s(self, mass_flow_kg_s):
        finite(mass_flow_kg_s, "mass flow")
        return None if mass_flow_kg_s == 0 else self.mass_kg.value / abs(mass_flow_kg_s)
