"""R12 functional intent graph. No plant solver or frozen M1 imports.

All generated device instances are G01 expansions of drawing templates, not
surveyed equipment. PID-005 disputed centreline is deliberately NOT an edge.
"""
from enum import Enum
from collections import deque


class CDU_IDENTITY(Enum):
    C01A = "C01A"
    C01B = "C01B"
    C02A = "C02A"
    C02B = "C02B"
    C03A = "C03A"
    C03B = "C03B"


class PRIMARY_NETWORK_ID(Enum):
    A = "A"
    B = "B"


class SECONDARY_NETWORK_ID(Enum):
    A = "A"
    B = "B"


def ref(source, locator):
    return {"source": source, "locator": locator}


P5 = [ref("S3", "PDF p6 PID-005")]
P6 = [ref("S3", "PDF p7 PID-006")]
P8 = [ref("S3", "PDF p3 PID-002; p9 PID-008")]
T2 = [ref("S2", "阀位矩阵!A8:O8"), ref("S3", "PDF p10 PID-009 T-2")]


def cdu_name(unit, side):
    if type(side) is not SECONDARY_NETWORK_ID:
        raise TypeError("SECONDARY_NETWORK_ID_REQUIRED")
    return f"G01-C{unit:02d}{side.value}"


def build_topology(intake):
    g = {"schema": "MEMPHIS-R12-FUNCTIONAL-GRAPH-v1", "revision": "R12-MAPPING-v1-build003",
         "admission": "PARTIALLY_MAPPED_BLOCKED",
         "bounded_test_scope": "DECLARED_FUNCTIONAL_INTENT_STATIC_AND_SYNTHETIC_UNIT_ONLY",
         "source_status": "R12_DRAFT_PROVIDED_REVISION_ALLOWED_ORIGINAL_PRESERVED",
         "dynamic_admission": False, "components": [], "ports": [], "edges": [],
         "sensors": [], "heat_couplings": [], "drawing_revisions": [
             {"id": "MAP-01", "change": "Disputed PID-005 straight-through line omitted from intent graph, not confirmed as real bypass", "issue": "R12-I06"},
             {"id": "MAP-02", "change": "Expand three independent A/B identities with qualified tags; no fixed CDU-to-primary mapping", "issue": "R12-I01"}],
         "open_runtime_values": {"measurement_freshness_s": None, "pump_follower_control": None,
             "pump_QH_NPSHr": None, "valve_travel_s": None, "M2_trigger_degC": None,
             "permissive_measurement_tolerances": None, "recharge_time_limit_s": None},
         "source_parameters": intake["parameters"], "source_issues": intake["open_issues"]}
    nodes = set()

    def component(tag, kind, sources, **extra):
        g["components"].append(dict(tag=tag, kind=kind, confirmation="SOURCE_DECLARED_TEMPLATE_EXPANSION",
            use="BOUNDED_INTENT_TEST_ONLY", source_refs=sources, **extra))

    def edge(tag, a, b, domain, sources, valves=(), pumps=(), primary=None, secondary=None, **extra):
        for node in (a, b):
            if node not in nodes:
                nodes.add(node)
                g["ports"].append(dict(id=node, equipment_tag=node.split(":")[0], fluid_domain=domain,
                    primary_network=primary, secondary_network=secondary,
                    primary_network_candidates=[primary] if primary is not None else [],
                    secondary_network_candidates=[secondary] if secondary is not None else [],
                    direction="SEE_INCIDENT_DIRECTED_BRANCHES", source_refs=sources,
                    confirmation="SOURCE_DECLARED_FUNCTIONAL_PORT", use="BOUNDED_INTENT_TEST_ONLY"))
            else:
                port=next(p for p in g["ports"] if p["id"]==node)
                if port["fluid_domain"] != domain:
                    raise ValueError("FLUID_DOMAIN_CONFLICT:"+node)
                for field,network in (("primary_network",primary),("secondary_network",secondary)):
                    if network is not None and network not in port[field+"_candidates"]:
                        port[field+"_candidates"].append(network)
                        port[field+"_candidates"].sort()
                    if len(port[field+"_candidates"])>1:
                        port[field]="SELECTABLE_A_OR_B_NOT_SIMULTANEOUS_AUTHORITY"
                port["source_refs"]=port["source_refs"]+[x for x in sources if x not in port["source_refs"]]
        record = dict(id=tag, equipment_tag=tag.split("/")[0], upstream=a, downstream=b,
            fluid_domain=domain, primary_network=primary, secondary_network=secondary,
            allowed_direction="UPSTREAM_TO_DOWNSTREAM", valve_dependencies=list(valves),
            pump_dependencies=list(pumps), sensor_dependencies=[], source_refs=sources,
            confirmation="SOURCE_DECLARED_FUNCTIONAL_BRANCH", use="BOUNDED_INTENT_TEST_ONLY", **extra)
        g["edges"].append(record)
        for v in valves:
            component(v, "VALVE", sources, upstream=a, downstream=b, fluid_domain=domain,
                      semantic="MODEL_AVAILABILITY_NOT_DRAWN_FIELD_VALVE" if "-FILTER" in v else "DRAWING_FUNCTIONAL_VALVE")
        for p in pumps:
            if not any(x["tag"] == p for x in g["components"]):
                component(p, "PUMP", sources, upstream=a, downstream=b, fluid_domain=domain)

    def sensor(tag, port, quantity, sources, channel=None):
        g["sensors"].append(dict(id=tag, port=port, quantity=quantity, channel=channel,
            source_refs=sources, provenance="REQUIRED_RELEASED_MEASUREMENT_NOT_PLANT_TRUTH",
            confirmation="PROPOSED_REQUIRED_INTERFACE_NOT_EXPLICITLY_DRAWN" if "-P1-FT-" in tag else "SOURCE_DECLARED_MEASUREMENT_TEMPLATE",
            physical_independence="DESIGN_REQUIREMENT_NOT_HARDWARE_VERIFIED"))

    for net in PRIMARY_NETWORK_ID:
        n = net.value
        component(f"G01-BT-{n}", "STRATIFIED_TANK", [ref("S3", "PDF p5 PID-004")], nominal_m3=15)
        edge(f"G01-LP-{n}/load-supply", f"G01-BT-{n}:BOTTOM_LOAD", f"G01-NET-{n}:SUP",
             "PG25_PRIMARY", [ref("S3", "PDF p5 PID-004")],
             valves=[f"G01-LP-{n}-I", f"G01-LP-{n}-O"], pumps=[f"G01-LP-{n}"], primary=n)
        edge(f"G01-NET-{n}/load-return", f"G01-NET-{n}:RET", f"G01-BT-{n}:TOP_LOAD",
             "PG25_PRIMARY", [ref("S3", "PDF p5 PID-004")], primary=n)
        edge(f"G01-SRC-H-{n}/source-draw", f"G01-BT-{n}:TOP_SOURCE", "G01-SRC:SUCTION",
             "PG25_PRIMARY", P8, valves=[f"G01-SRC-H-{n}"], primary=n)
        edge(f"G01-SRC-S-{n}/source-supply", "G01-SRC:DISCHARGE", f"G01-SRC-{n}:HOT",
             "PG25_PRIMARY", P8, valves=[f"G01-SRC-S-{n}"], primary=n)
        for src in ("D1", "D2", "W1", "W2"):
            edge(f"G01-{src}/{n}-in", f"G01-SRC-{n}:HOT", f"G01-{src}:IN", "PG25_PRIMARY", P8,
                 valves=[f"G01-{src}-CV-{n}S"], primary=n)
            edge(f"G01-{src}/{n}-out", f"G01-{src}:OUT", f"G01-BT-{n}:BOTTOM_SOURCE", "PG25_PRIMARY", P8,
                 valves=[f"G01-{src}-CV-{n}R"], primary=n)
        sensor(f"G01-NET-{n}-P1-PDT-SYS-CH1", f"G01-NET-{n}:SUP", "differential_pressure_kPa", P8, "CH1")
    for i in range(1, 5):
        edge(f"G01-SP{i:02d}/pump", "G01-SRC:SUCTION", "G01-SRC:DISCHARGE", "PG25_PRIMARY", P8,
             pumps=[f"G01-SP{i:02d}"])
    for src in ("D1", "D2", "W1", "W2"):
        component(f"G01-{src}", "SOURCE_UNIT", P8, performance_status="OEM_UNVERIFIED")
        edge(f"G01-{src}/coil", f"G01-{src}:IN", f"G01-{src}:OUT", "PG25_PRIMARY", P8)
    for ch in ("CH1", "CH2"):
        sensor(f"G01-SRC-FT-{ch}", "G01-SRC:DISCHARGE", "flow_m3_h", P8, ch)
    for u in range(1, 4):
        for sec in SECONDARY_NETWORK_ID:
            s = sec.value
            c = cdu_name(u, sec)
            identity = CDU_IDENTITY[c.removeprefix("G01-")]
            component(c, "CDU", P5 + P6, CDU_IDENTITY=identity.value, unit=u,
                      secondary_network=s, selectable_primary_networks=["A", "B"],
                      primary_selection_independent=True)
            for net in PRIMARY_NETWORK_ID:
                n = net.value
                edge(c + f"/P1-{n}-supply", f"G01-NET-{n}:SUP", c + ":P1-IN", "PG25_PRIMARY", P5,
                     valves=[c + f"-P1-CV-{n}S"], primary=n)
                edge(c + f"/P1-{n}-return", c + ":P1-OUT", f"G01-NET-{n}:RET", "PG25_PRIMARY", P5,
                     valves=[c + f"-P1-CV-{n}R"], primary=n)
            edge(c + "/HX-primary", c + ":P1-IN", c + ":P1-OUT", "PG25_PRIMARY", P5)
            domain = f"PG25_SECONDARY_U{u}"
            edge(c + "/return-isolation", f"G01-U{u}-P2-{s}:RET", c + ":P2-SUCTION", domain, P5,
                 valves=[c + "-P2-XV-RET"], secondary=s)
            for pi in (1, 2):
                edge(c + f"/P2-pump-{pi}", c + ":P2-SUCTION", c + ":P2-DISCHARGE", domain, P5,
                     pumps=[c + f"-P2-PM{pi}"], secondary=s, duty="ONE_DUTY_ONE_STANDBY_2x100_PERCENT")
            for fi in (1, 2):
                edge(c + f"/P2-filter-{fi}", c + ":P2-DISCHARGE", c + ":P2-HX-IN", domain, P5,
                     valves=[c + f"-FILTER{fi}-SERVICE"], secondary=s,
                     qualification="FUNCTIONAL_FILTER_SELECTION_ABSTRACTION_OEM_ISOLATION_TAGS_UNRESOLVED")
            edge(c + "/HX-secondary", c + ":P2-HX-IN", c + ":P2-HX-OUT", domain, P5, secondary=s)
            edge(c + "/supply-isolation", c + ":P2-HX-OUT", f"G01-U{u}-P2-{s}:SUP", domain, P5,
                 valves=[c + "-P2-XV-SUP"], secondary=s)
            g["heat_couplings"].append(dict(id=c + "/HX-HEAT", primary_edge=c + "/HX-primary",
                secondary_edge=c + "/HX-secondary", fluid_mixing=False, source_refs=P5,
                UA_actual=None, use="BASIC_INTERFACE_UNIT_TEST_ONLY"))
            for ch in ("CH1", "CH2"):
                for prefix, port, quantity in (("P1-FT", ":P1-IN", "flow_m3_h"),
                      ("P1-TT", ":P1-IN", "temperature_C"), ("P2-FT", ":P2-HX-OUT", "flow_m3_h"),
                      ("P2-TT", ":P2-HX-OUT", "temperature_C")):
                    sensor(c + "-" + prefix + "-" + ch, c + port, quantity, P5, ch)
            sensor(c + "-PT-SUC", c + ":P2-SUCTION", "pressure_kPa_g", P5)
        for ri in range(1, 7):
            rack = f"G01-U{u}-R{ri:02d}"
            component(rack, "RACK_LOAD", P6, unit=u, rack=ri,
                      liquid_heat_kW=intake["parameters"]["single_rack_liquid_heat"]["value"])
            for sec in SECONDARY_NETWORK_ID:
                s = sec.value
                edge(rack + f"/{s}-supply", f"G01-U{u}-P2-{s}:SUP", rack + ":IN", f"PG25_SECONDARY_U{u}", P6,
                     valves=[rack + f"-CV-{s}S"], secondary=s)
                edge(rack + f"/{s}-return", rack + ":OUT", f"G01-U{u}-P2-{s}:RET", f"PG25_SECONDARY_U{u}", P6,
                     valves=[rack + f"-CV-{s}R"], secondary=s)
                for ch in ("CH1", "CH2"):
                    sensor(rack + f"-FT-{s}S-" + ch, rack + ":IN", "flow_m3_h", P6, ch)
            edge(rack + "/heat-load", rack + ":IN", rack + ":OUT", f"PG25_SECONDARY_U{u}", P6)
            for ch in ("CH1", "CH2"):
                sensor(rack + "-TT-IN-" + ch, rack + ":IN", "temperature_C", P6, ch)
    for e in g["edges"]:
        e["sensor_dependencies"] = [s["id"] for s in g["sensors"] if s["port"] in (e["upstream"], e["downstream"])]
    return g


def enabled_edges(g, valves, pumps):
    # Actual feedback only. Missing is closed/stopped, never command-as-proof.
    return [e for e in g["edges"] if all(valves.get(v) is True for v in e["valve_dependencies"])
            and all(pumps.get(p) is True for p in e["pump_dependencies"])]


def path(edges, start, end):
    q = deque([(start, [])]); seen = {start}
    while q:
        at, trail = q.popleft()
        if at == end:
            return trail
        for e in edges:
            if e["upstream"] == at and e["downstream"] not in seen:
                seen.add(e["downstream"]); q.append((e["downstream"], trail + [e["id"]]))
    return None


def isolation_errors(g, valves):
    errors = []
    for c in (x for x in g["components"] if x["kind"] == "CDU"):
        tag = c["tag"]
        opened = {(n, d) for n in ("A", "B") for d in ("S", "R") if valves.get(tag + f"-P1-CV-{n}{d}")}
        if len({n for n, _ in opened}) > 1:
            errors.append("PRIMARY_CROSS_CONNECT:" + tag)
        for n in ("A", "B"):
            if ((n, "S") in opened) != ((n, "R") in opened):
                errors.append("UNPAIRED_PRIMARY:" + tag)
    src_networks = {n for n in ("A", "B") if any(valves.get(f"G01-SRC-{d}-{n}") for d in ("H", "S"))}
    for src in ("D1", "D2", "W1", "W2"):
        sides = {n for n in ("A", "B") if any(valves.get(f"G01-{src}-CV-{n}{d}") for d in ("S", "R"))}
        if len(sides) > 1:
            errors.append("SOURCE_CROSS_CONNECT:" + src)
        src_networks |= sides
        for n in ("A", "B"):
            if bool(valves.get(f"G01-{src}-CV-{n}S")) != bool(valves.get(f"G01-{src}-CV-{n}R")):
                errors.append("UNPAIRED_SOURCE:" + src)
    if len(src_networks) > 1:
        errors.append("COMMON_SOURCE_PRIMARY_CROSS_CONNECT")
    for n in ("A", "B"):
        if bool(valves.get(f"G01-SRC-H-{n}")) != bool(valves.get(f"G01-SRC-S-{n}")):
            errors.append("UNPAIRED_SOURCE_HEADER:" + n)
    return sorted(set(errors))


def operating_fixture(g, primary=PRIMARY_NETWORK_ID.A, secondary=SECONDARY_NETWORK_ID.A):
    """Synthetic unit fixture only; not a hydraulic solution or a PLC receipt."""
    if type(primary) is not PRIMARY_NETWORK_ID or type(secondary) is not SECONDARY_NETWORK_ID:
        raise TypeError("NETWORK_ENUM_SPACES_ARE_NOT_INTERCHANGEABLE")
    v = {x["tag"]: False for x in g["components"] if x["kind"] == "VALVE"}
    p = {x["tag"]: False for x in g["components"] if x["kind"] == "PUMP"}
    n, s = primary.value, secondary.value
    p[f"G01-LP-{n}"] = True
    v[f"G01-LP-{n}-I"] = v[f"G01-LP-{n}-O"] = True
    for u in range(1, 4):
        c = cdu_name(u, secondary)
        for suffix in (f"-P1-CV-{n}S", f"-P1-CV-{n}R", "-P2-XV-RET", "-P2-XV-SUP", "-FILTER1-SERVICE"):
            v[c + suffix] = True
        p[c + "-P2-PM1"] = True
        for r in range(1, 7):
            v[f"G01-U{u}-R{r:02d}-CV-{s}S"] = v[f"G01-U{u}-R{r:02d}-CV-{s}R"] = True
    return dict(valves=v, pumps=p, primary_network=n, secondary_network=s,
                CDU_IDENTITY=[cdu_name(u, secondary).removeprefix("G01-") for u in range(1, 4)],
                provenance="SYNTHETIC_UNIT_FIXTURE_NOT_PLC_OR_PHYSICAL_EVIDENCE")


def connectivity(g, f):
    edges = enabled_edges(g, f["valves"], f["pumps"])
    n = f["primary_network"]; s = f["secondary_network"]
    rows = []
    for u in range(1, 4):
        c = f"G01-C{u:02d}{s}"
        supply = path(edges, f"G01-BT-{n}:BOTTOM_LOAD", c + ":P1-IN")
        ret = path(edges, c + ":P1-OUT", f"G01-BT-{n}:TOP_LOAD")
        racks = []
        for r in range(1, 7):
            tag = f"G01-U{u}-R{r:02d}"
            # Return crosses pump and filter before entering secondary HX.
            a = path(edges, c + ":P2-HX-OUT", tag + ":IN")
            b = path(edges, tag + ":OUT", c + ":P2-HX-IN")
            racks.append(dict(rack=tag, supply_path=a, return_path=b, connected=a is not None and b is not None))
        rows.append(dict(CDU=c, primary_supply_path=supply, primary_return_path=ret,
                         primary_connected=supply is not None and ret is not None, racks=racks))
    return dict(isolation_errors=isolation_errors(g, f["valves"]), units=rows,
                scope="STATIC_ACTUAL_FEEDBACK_FIXTURE_CONNECTIVITY_NOT_FLOW_MAGNITUDE")


def heat_interface(g, fixture, measured_unit_flows):
    """Conditional port-bookkeeping contract, NOT a heat-exchanger capacity law.

Flows are synthetic external inputs in unit tests. Capacity/UA, stored energy,
and temperature dynamics are not computed. Disconnected heat cannot disappear.
"""
    graph_proof=connectivity(g,fixture)
    units=[]
    for index,proof in enumerate(graph_proof["units"]):
        load=sum(c["liquid_heat_kW"] for c in g["components"] if c["kind"]=="RACK_LOAD" and c["unit"]==index+1)
        primary,secondary=measured_unit_flows[index]
        valid=(not graph_proof["isolation_errors"] and proof["primary_connected"] and
               all(r["connected"] for r in proof["racks"]) and primary>0 and secondary>0)
        assigned=load if valid else 0.
        units.append(dict(CDU=proof["CDU"],rack_liquid_kW=load,HX_secondary_removed_kW=assigned,
                          HX_primary_received_kW=assigned,unremoved_load_kW=load-assigned,
                          closure_error_kW=load-assigned-(load-assigned),
                          primary_flow_fixture_m3_h=primary,secondary_flow_fixture_m3_h=secondary,
                          scope="CONDITIONAL_BOOKKEEPING_NOT_ACTUAL_CAPACITY_OR_THERMAL_SOLUTION"))
    return units
