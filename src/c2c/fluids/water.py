from dataclasses import dataclass


@dataclass(frozen=True)
class ConstantFluid:
    name: str
    density_kg_m3: float
    cp_j_kgk: float

    def mass_flow(self, volumetric_flow_m3_s: float) -> float:
        return max(0.0, volumetric_flow_m3_s) * self.density_kg_m3
