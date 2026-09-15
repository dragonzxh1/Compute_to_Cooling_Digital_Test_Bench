from pint import UnitRegistry

ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
Q_ = ureg.Quantity


def m3h_to_m3s(value: float) -> float:
    return Q_(value, "m^3/hour").to("m^3/second").magnitude


def m3s_to_m3h(value: float) -> float:
    return Q_(value, "m^3/second").to("m^3/hour").magnitude
