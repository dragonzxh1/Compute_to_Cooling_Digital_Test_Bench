from c2c.fluids.water import ConstantFluid


def pg25(density_kg_m3: float = 1020.0, cp_j_kgk: float = 3900.0) -> ConstantFluid:
    """Constant-property planning approximation, not a validated correlation."""
    return ConstantFluid("pg25", density_kg_m3, cp_j_kgk)
