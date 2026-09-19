"""Small externally assembled NUMERICAL_TEST_FIXTURE configurations, not OEM data."""

from dataclasses import dataclass, replace

from .coldplate import ColdplateDefinition, FlowInput, GenericColdplate
from .interfaces import InterfaceKind, ThermalInterface
from .nodes import NodeType, ThermalNodeState
from .provenance import fixture_parameter as p
from .source_mapping import PowerLeaf, PowerSourceMap
from .state import ThermalState
from .topology import ThermalTopology


def node(
    name, kind=NodeType.GPU_DIE, capacity=100.0, temperature=300.0, *, adiabatic=False, owner=None
):
    c = p(f"{name}.C", capacity, "J/K")
    kwargs = {}
    if kind == NodeType.LOCAL_COOLANT:
        kwargs = {
            "mass_kg": p(f"{name}.mass", capacity / 4000, "kg"),
            "specific_heat": p(f"{name}.cp", 4000, "J/(kg*K)"),
            "coolant": "fixture_water",
        }
    return ThermalNodeState(
        name,
        name.split(":")[0],
        kind,
        temperature,
        capacity * (temperature - 300),
        c,
        300,
        owner or f"storage:{name}",
        (250.0, 500.0),
        c,
        "UNVALIDATED",
        adiabatic=adiabatic,
        **kwargs,
    )


def leaf(name="power", power=100.0, kind="GPU_DIE", component=None):
    return PowerLeaf(name, kind, p(name, power, "W"), frozenset({component or name}))


def resistor(name, hot, cold, resistance, *, boundary=False, medium=None, layers=None):
    r = p(name + ".R", resistance, "K/W")
    return ThermalInterface(
        name,
        hot,
        None if boundary else cold,
        cold if boundary else None,
        r,
        layers or (f"{name}:RESISTANCE",),
        f"owner:{name}",
        InterfaceKind.PRESCRIBED_BOUNDARY if boundary else InterfaceKind.CONDUCTIVE_RESISTANCE,
        r,
        boundary_medium=medium,
    )


def coldplate_model(hot="plate", cold="coolant", conduction_r=0.02):
    definition = ColdplateDefinition(
        hot,
        cold,
        "REPRESENTATIVE_PLATE_SOLID",
        "LOCAL_WELL_MIXED_BULK",
        "COLDPLATE_SOLID_TO_LOCAL_BULK_COOLANT",
        (f"{hot}:PLATE_INTERNAL_CONDUCTION", f"{hot}:PLATE_TO_COOLANT_CONVECTION"),
        (f"{hot}:DIE_PACKAGE", f"{hot}:PACKAGE_TIM", f"{hot}:TIM_CONTACT"),
    )
    return GenericColdplate(
        definition,
        p("h_ref", 1000, "W/(m2*K)"),
        p("m_ref", 0.1, "kg/s"),
        p("exponent", 0.7, "fraction"),
        p("R_conduction", conduction_r, "K/W"),
        p("area", 0.02, "m2"),
        (0.01, 0.5),
        (250.0, 500.0),
        (0.0, 10000.0),
        "fixture_water",
        p("model_revision", 1, "count"),
    )


def coldplate_edge(model, name="cp"):
    d = model.definition
    return ThermalInterface(
        name,
        d.thermal_hot_endpoint_id,
        d.thermal_cold_endpoint_id,
        None,
        model,
        d.included_layers,
        f"owner:{name}",
        InterfaceKind.COLDPLATE_FLOW_DEPENDENT,
        model.provenance,
    )


def flow(value=0.1, coolant="fixture_water"):
    return FlowInput(p("local_mass_flow", value, "kg/s"), coolant)


@dataclass(frozen=True)
class Fixture:
    topology: ThermalTopology
    source_map: PowerSourceMap
    sources: tuple[PowerLeaf, ...]
    boundaries: tuple[tuple[str, object], ...] = ()
    flows: tuple[tuple[str, FlowInput], ...] = ()


def insulated(power=100.0):
    state = ThermalState((node("die", adiabatic=True),))
    return Fixture(
        ThermalTopology(state, (), (("device", ("die",)),)),
        PowerSourceMap((("power", "die"),)),
        (leaf(power=power),),
    )


def linear_rc():
    state = ThermalState((node("die", temperature=320.0),))
    topology = ThermalTopology(
        state,
        (resistor("sink", "die", "ambient", 0.5, boundary=True, medium="AIR"),),
        (("device", ("die",)),),
    )
    return Fixture(topology, PowerSourceMap(()), (), (("ambient", p("T_ambient", 300, "K")),))


def pair():
    state = ThermalState(
        (
            node("a", capacity=100, temperature=320),
            node("b", NodeType.GPU_PACKAGE, capacity=200, temperature=290),
        )
    )
    return Fixture(
        ThermalTopology(state, (resistor("ab", "a", "b", 0.5),), (("device", ("a", "b")),)),
        PowerSourceMap(()),
        (),
    )


def gpu_chain(air_r=0.8, conduction_r=0.02, power=120.0, with_hbm=False):
    nodes = (
        node("die", capacity=200),
        node("package", NodeType.GPU_PACKAGE, 400),
        node("plate", NodeType.COLD_PLATE, 800),
        node("coolant", NodeType.LOCAL_COOLANT, 2000),
    )
    edges = (
        resistor("die_package", "die", "package", 0.05, layers=("gpu:DIE_PACKAGE",)),
        resistor("tim", "package", "plate", 0.03, layers=("gpu:TIM_CONTACT",)),
        coldplate_edge(coldplate_model(conduction_r=conduction_r)),
        resistor("air", "package", "ambient", air_r, boundary=True, medium="AIR"),
        resistor("liquid_sink", "coolant", "bath", 0.02, boundary=True, medium="LIQUID"),
    )
    sources, mapping = (leaf(power=power),), (("power", "die"),)
    if with_hbm:
        nodes += (node("hbm", NodeType.HBM, 150), node("board", NodeType.VRM_BOARD, 200))
        edges += (
            resistor("hbm_plate", "hbm", "plate", 0.08),
            resistor("board_air", "board", "ambient", 0.5, boundary=True, medium="AIR"),
        )
        sources += (leaf("hbm_power", 20, "HBM"), leaf("board_power", 10, "VRM_BOARD"))
        mapping += (("hbm_power", "hbm"), ("board_power", "board"))
    device_nodes = tuple(n.node_id for n in nodes if n.node_id not in {"plate", "coolant"})
    topology = ThermalTopology(ThermalState(nodes), edges, (("device", device_nodes),))
    return Fixture(
        topology,
        PowerSourceMap(mapping),
        sources,
        (("ambient", p("T_air", 300, "K")), ("bath", p("T_test_bath", 300, "K"))),
        (("cp", flow()),),
    )


def with_power(fixture, power):
    first = replace(fixture.sources[0], power=p(fixture.sources[0].source_id, power, "W"))
    return replace(fixture, sources=(first, *fixture.sources[1:]))
