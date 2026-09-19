"""Small generic physical loops; all values are unvalidated numerical fixtures."""

from v0_2.cdu.heat_exchanger import Arrangement, HeatExchanger
from v0_2.coolant.volume import CoolantVolumeState
from v0_2.fluids.properties import ConstantCpFluid
from v0_2.hydraulics.graph import EdgeKind, HydraulicEdge, HydraulicGraph, PressureNode
from v0_2.hydraulics.pump import PumpCurve, PumpDrive
from v0_2.plant.loop import FluidConnection, PhysicalPlant, PlantInput, PlantState
from v0_2.thermal.fixtures import coldplate_edge, coldplate_model, leaf, node, resistor
from v0_2.thermal.nodes import NodeType
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.source_mapping import PowerSourceMap
from v0_2.thermal.validity import require


def generic_fluid(name="fixture_water"):
    return ConstantCpFluid(
        name,
        p(f"{name}.rho", 1000.0, "kg/m3"),
        p(f"{name}.cp", 4000.0, "J/(kg*K)"),
        p(f"{name}.Tref", 300.0, "K"),
        (250.0, 500.0),
        p(f"{name}.model", 1, "count"),
    )


def volume(name, fluid, mass=0.5, temperature=300.0):
    initial_pressure = p(f"{name}.initial_pressure", 101325.0, "Pa")
    return CoolantVolumeState(
        name,
        p(f"{name}.mass", mass, "kg"),
        fluid.h(temperature),
        temperature,
        initial_pressure.value,
        fluid.fluid_id,
        f"storage:{name}",
        fluid,
        p(f"{name}.provenance", 1, "count"),
    )


def edge(name, a, b, k, receiver):
    return HydraulicEdge(
        name,
        a,
        b,
        EdgeKind.GENERIC_RESISTANCE,
        p(f"{name}.K", k, "Pa/(m3/s)^2"),
        (0.0, 0.01),
        receiver,
        p(f"{name}.liquid_fraction", 1.0, "fraction"),
        p(f"{name}.provenance", 1, "count"),
    )


def physical_fixture(branch_count=2, power_each=120.0, branch_multiplier=None):
    require(
        type(branch_count) is int and 1 <= branch_count <= 4,
        "INVALID_RANGE",
        "mini fixture supports one to four branches",
    )
    fluid = generic_fluid()
    primary = generic_fluid("fixture_primary")
    solids, volumes, interfaces, connections, cp_map, source_map, sources = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    pressure_map = []

    def add_volume(name, mass=0.5, pressure_node="r0"):
        volumes.append(volume(name, fluid, mass))
        pressure_map.append((name, pressure_node))

    add_volume("cdu", 2.0)
    add_volume("supply_0", pressure_node="sp1")
    add_volume("supply_1", pressure_node="sm")
    add_volume("supply_manifold", pressure_node="sm")
    add_volume("return_manifold", pressure_node="rm")
    add_volume("return_0", pressure_node="rp1")
    add_volume("return_1")
    for a, b in (
        ("cdu", "supply_0"),
        ("supply_0", "supply_1"),
        ("supply_1", "supply_manifold"),
        ("return_manifold", "return_0"),
        ("return_0", "return_1"),
        ("return_1", "cdu"),
    ):
        connections.append(FluidConnection(f"fluid:{a}->{b}", a, b))

    graph_nodes = [
        PressureNode(name, "secondary") for name in ("r0", "po", "sp1", "sm", "rm", "rp1")
    ]
    supply = (
        edge("supply_pipe_0", "po", "sp1", 5e10, "supply_0"),
        edge("supply_pipe_1", "sp1", "sm", 5e10, "supply_1"),
    )
    ret = (
        edge("return_pipe_0", "rm", "rp1", 5e10, "return_0"),
        edge("return_pipe_1", "rp1", "r0", 5e10, "return_1"),
    )
    hydraulic_branches = []
    for i in range(branch_count):
        die, package, plate, local, branch_return = (
            f"b{i}:{part}" for part in ("die", "package", "plate", "local", "return")
        )
        graph_nodes.append(PressureNode(f"bm{i}", "secondary"))
        add_volume(local, pressure_node=f"bm{i}")
        add_volume(branch_return, pressure_node="rm")
        solids.extend(
            (
                node(die, NodeType.GPU_DIE, 200),
                node(package, NodeType.GPU_PACKAGE, 400),
                node(plate, NodeType.COLD_PLATE, 800),
            )
        )
        interfaces.extend(
            (
                resistor(f"b{i}:die_package", die, package, 0.05, layers=(f"b{i}:DIE_PACKAGE",)),
                resistor(f"b{i}:TIM", package, plate, 0.03, layers=(f"b{i}:TIM_CONTACT",)),
                coldplate_edge(coldplate_model(plate, local), f"b{i}:cp"),
                resistor(f"b{i}:air", package, "ambient", 0.8, boundary=True, medium="AIR"),
            )
        )
        cp_map.append((f"b{i}:cp", i))
        source_map.append((f"b{i}:power", die))
        sources.append(leaf(f"b{i}:power", power_each, "GPU_DIE"))
        connections.extend(
            (
                FluidConnection(f"fluid:sm->b{i}", "supply_manifold", local, i),
                FluidConnection(f"fluid:b{i}->return", local, branch_return, i),
                FluidConnection(f"fluid:b{i}->rm", branch_return, "return_manifold", i),
            )
        )
        mult = branch_multiplier if i == 0 and branch_multiplier is not None else 1.0
        hydraulic_branches.append(
            (
                edge(f"b{i}:coldplate_dp", "sm", f"bm{i}", 1e12 * mult, local),
                edge(f"b{i}:branch_pipe", f"bm{i}", "rm", 1e12, branch_return),
            )
        )
    graph = HydraulicGraph(
        tuple(graph_nodes), "r0", "po", "sm", "rm", supply, tuple(hydraulic_branches), ret, "pump"
    )
    curve = PumpCurve(
        p("pump.shutoff", 60000, "Pa"),
        p("pump.K", 1e11, "Pa/(m3/s)^2"),
        (0.0, 1.0),
        (0.0, 0.01),
        p("pump.model", 1, "count"),
    )
    drive = PumpDrive(
        p("eta.vfd", 0.9, "fraction"),
        p("eta.motor", 0.8, "fraction"),
        p("eta.pump", 0.75, "fraction"),
        p("vfd.to_liquid", 0, "fraction"),
        p("motor.to_liquid", 0.5, "fraction"),
        p("pump.to_liquid", 1, "fraction"),
        "cdu",
        p("drive.model", 1, "count"),
        p("drive.standby", 0, "W"),
    )
    hx = HeatExchanger(
        p("hx.UA", 100, "W/K"),
        Arrangement.COUNTERFLOW,
        fluid,
        primary,
        (0.0, 2.0),
        (0.0, 2.0),
        p("hx.rated", 5000, "W"),
        p("hx.model", 1, "count"),
    )
    plant = PhysicalPlant(
        PlantState(tuple(solids), tuple(volumes)),
        tuple(interfaces),
        tuple(connections),
        tuple(cp_map),
        graph,
        curve,
        drive,
        hx,
        PowerSourceMap(tuple(source_map)),
        "cdu",
        tuple(pressure_map),
        p("plant.model", 1, "count"),
        p("plant.pressure_reference", 101325, "Pa"),
    )
    controls = PlantInput(
        p("pump.speed_actual", 0.9, "fraction"),
        p("fws.primary_m", 0.4, "kg/s"),
        p("fws.inlet", 290, "K"),
        p("ambient", 300, "K"),
        tuple(sources),
    )
    return plant, controls
