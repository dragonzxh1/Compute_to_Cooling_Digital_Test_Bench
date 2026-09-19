from dataclasses import dataclass
from enum import StrEnum
from math import exp, expm1

from v0_2.fluids.properties import ConstantCpFluid
from v0_2.thermal.provenance import ParameterRecord
from v0_2.thermal.validity import ValidityStatus, finite, require


class Arrangement(StrEnum):
    COUNTERFLOW = "COUNTERFLOW"
    PARALLEL = "PARALLEL"


@dataclass(frozen=True)
class HeatExchanger:
    ua: ParameterRecord
    arrangement: Arrangement
    secondary_fluid: ConstantCpFluid
    primary_fluid: ConstantCpFluid
    valid_secondary_flow: tuple[float, float]
    valid_primary_flow: tuple[float, float]
    rated_capacity_w: ParameterRecord | None
    provenance: ParameterRecord

    def __post_init__(self):
        require(self.ua.si("W/K") > 0, "HX_UA", "positive UA")
        require(isinstance(self.arrangement, Arrangement), "HX_ARRANGEMENT", "unknown")
        require(
            self.secondary_fluid.fluid_id != self.primary_fluid.fluid_id,
            "PRIMARY_SECONDARY_MIX",
            "distinct loop identities",
        )
        for bounds in (self.valid_primary_flow, self.valid_secondary_flow):
            require(
                type(bounds) is tuple and len(bounds) == 2 and 0 <= bounds[0] < bounds[1],
                "INVALID_RANGE",
                "HX flow",
            )
        if self.rated_capacity_w is not None:
            require(self.rated_capacity_w.si("W") > 0, "HX_CAPACITY", "rated")


@dataclass(frozen=True)
class HXExchange:
    secondary_inlet_k: float
    secondary_outlet_k: float
    primary_inlet_k: float
    primary_outlet_k: float
    secondary_mass_flow_kg_s: float
    primary_mass_flow_kg_s: float
    effectiveness: float
    secondary_out_w: float
    primary_in_w: float


def evaluate(hx, secondary_flow, primary_flow, secondary_inlet_k, primary_inlet_k):
    for q, bounds in (
        (secondary_flow, hx.valid_secondary_flow),
        (primary_flow, hx.valid_primary_flow),
    ):
        finite(q, "HX flow")
        require(
            bounds[0] <= q <= bounds[1],
            "HX_FLOW_OUT_OF_RANGE",
            str(q),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
    hx.secondary_fluid.h(secondary_inlet_k)
    hx.primary_fluid.h(primary_inlet_k)
    if secondary_flow == 0 or primary_flow == 0:
        return HXExchange(
            secondary_inlet_k,
            secondary_inlet_k,
            primary_inlet_k,
            primary_inlet_k,
            secondary_flow,
            primary_flow,
            0.0,
            0.0,
            0.0,
        )
    c_s = secondary_flow * hx.secondary_fluid.specific_heat.value
    c_p = primary_flow * hx.primary_fluid.specific_heat.value
    c_min, c_max = min(c_s, c_p), max(c_s, c_p)
    cr = c_min / c_max
    ntu = hx.ua.value / c_min
    if hx.arrangement == Arrangement.PARALLEL:
        effectiveness = -expm1(-ntu * (1 + cr)) / (1 + cr)
    elif abs(1 - cr) < 1e-10:
        effectiveness = ntu / (1 + ntu)
    else:
        e = exp(-ntu * (1 - cr))
        effectiveness = (1 - e) / (1 - cr * e)
    heat = effectiveness * c_min * (secondary_inlet_k - primary_inlet_k)
    if hx.rated_capacity_w is not None:
        require(
            abs(heat) <= hx.rated_capacity_w.value,
            "HX_CAPACITY_OUT_OF_RANGE",
            str(heat),
            ValidityStatus.MODEL_OUT_OF_RANGE,
        )
    secondary_out = secondary_inlet_k - heat / c_s
    primary_out = primary_inlet_k + heat / c_p
    hx.secondary_fluid.h(secondary_out)
    hx.primary_fluid.h(primary_out)
    return HXExchange(
        secondary_inlet_k,
        secondary_out,
        primary_inlet_k,
        primary_out,
        secondary_flow,
        primary_flow,
        effectiveness,
        heat,
        heat,
    )
