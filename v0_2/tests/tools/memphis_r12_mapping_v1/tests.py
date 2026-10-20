"""Independent expected assertions and synthetic observation fixtures.

These values exercise branches, not OEM performance or actual PLC observations.
No physical time integration takes place. Test raw input records are saved.
"""
import copy
import json
import math
from .topology import (CDU_IDENTITY, PRIMARY_NETWORK_ID as P, SECONDARY_NETWORK_ID as S,
                       cdu_name, operating_fixture, connectivity, isolation_errors, enabled_edges, path)
from .control import T2Controller, T1Controller, RechargeController, UnitPolicy


POLICY = UnitPolicy(.5, .5, 40.)  # Explicit unit-test policy, not approved R12 setpoints.


def observation(g, time=0., stage="primary"):
    f = operating_fixture(g)
    a, b = cdu_name(1, S.A), cdu_name(1, S.B)
    # Newly connected CDU B uses A primary, NEVER a B-tank route.
    f["valves"][b+"-P1-CV-AS"] = f["valves"][b+"-P1-CV-AR"] = True
    o = dict(f)
    o.update(id=f"TEST-OBS-{time}-{stage}", sample_s=time, release_s=time,
        provenance="SYNTHETIC_RELEASED_UNIT_MEASUREMENTS", channels_independent_fixture=True,
        delta_T_K=[1., 1.1], delta_p_kPa=[2., 2.1], new_primary_flow_m3_h=[110.,110.],
        new_secondary_flow_m3_h=[0.,0.], rack_flow_m3_h=[[0.,0.] for _ in range(6)],
        pressure_masters=[a], old_master_revoked=False, old_pump_speed_pct=[60.,0.],
        new_secondary_temperature_C=[42.,42.],rack_temperature_C=[[42.,42.] for _ in range(6)])
    if stage in ("overlap", "revoked", "isolated", "master"):
        for suffix in ("-P2-XV-RET", "-P2-XV-SUP", "-FILTER1-SERVICE"):
            o["valves"][b+suffix] = True
        o["pumps"][b+"-P2-PM1"] = True
        for r in range(1,7):
            o["valves"][f"G01-U1-R{r:02d}-CV-BS"] = o["valves"][f"G01-U1-R{r:02d}-CV-BR"] = True
        o["new_secondary_flow_m3_h"] = [68.37,68.37]
        o["rack_flow_m3_h"] = [[11.395,11.395] for _ in range(6)]
    if stage in ("revoked", "isolated", "master"):
        o["pressure_masters"] = []; o["old_master_revoked"] = True
        o["old_pump_speed_pct"] = [0.,0.]
        o["pumps"][a+"-P2-PM1"] = False
    if stage in ("isolated", "master"):
        for suffix in ("-P2-XV-RET", "-P2-XV-SUP", "-P1-CV-AS", "-P1-CV-AR"):
            o["valves"][a+suffix] = False
        for r in range(1,7):
            o["valves"][f"G01-U1-R{r:02d}-CV-AS"] = o["valves"][f"G01-U1-R{r:02d}-CV-AR"] = False
    if stage == "master":
        o["pressure_masters"] = [b]
    return o


def t2_trace(g, mutate=None, end=7.):
    c = T2Controller(g,1,P.A,S.A,S.B,POLICY); inputs = []
    for tick in range(int(end*2)+1):
        t = tick/2
        stage = "primary" if t<=5 else "overlap" if t==5.5 else "revoked" if t==6 else "isolated" if t==6.5 else "master"
        o = observation(g,t,stage)
        if mutate:
            mutate(o,t)
        inputs.append(copy.deepcopy(o)); c.step(o,t)
    return c, inputs


def source_fixture(g, net="A", source="D1", running=True):
    f = operating_fixture(g)
    f["valves"][f"G01-SRC-H-{net}"] = f["valves"][f"G01-SRC-S-{net}"] = True
    f["valves"][f"G01-{source}-CV-{net}S"] = f["valves"][f"G01-{source}-CV-{net}R"] = True
    for i in (1,2,3):
        f["pumps"][f"G01-SP{i:02d}"] = running
    return f


def validate_schema(g):
    assert g["admission"] == "PARTIALLY_MAPPED_BLOCKED" and g["dynamic_admission"] is False
    for collection, key in (("components","tag"),("ports","id"),("edges","id"),("sensors","id")):
        keys = [x[key] for x in g[collection]]
        assert len(keys) == len(set(keys)), ("DUPLICATE", collection)
    ports = {x["id"]:x for x in g["ports"]}
    components = {x["tag"]:x for x in g["components"]}
    for e in g["edges"]:
        assert e["upstream"] in ports and e["downstream"] in ports
        assert ports[e["upstream"]]["fluid_domain"] == ports[e["downstream"]]["fluid_domain"] == e["fluid_domain"]
        assert e["source_refs"] and all(x["source"] in ("S2","S3","S4") and x["locator"] for x in e["source_refs"])
        assert all(v in components for v in e["valve_dependencies"] + e["pump_dependencies"])
    for s in g["sensors"]:
        assert s["port"] in ports and s["source_refs"]
    assert len([c for c in g["components"] if c["kind"] == "CDU"]) == 6
    assert len([c for c in g["components"] if c["kind"] == "RACK_LOAD"]) == 18
    assert len([c for c in g["components"] if "-P2-PM" in c["tag"]]) == 12
    assert len([c for c in g["components"] if "-R" in c["tag"] and "-CV-" in c["tag"]]) == 72
    assert not any("BYPASS" in e["id"] for e in g["edges"])
    assert not any(c["tag"].startswith(("RC", "CP-")) for c in g["components"])
    assert g["open_runtime_values"]["M2_trigger_degC"] is None
    return {"components":len(components),"ports":len(ports),"edges":len(g["edges"]),"sensors":len(g["sensors"])}


def run_tests(g):
    results=[]
    def check(id, negative, expected, execute, grounds):
        try:
            evidence=execute()
            record=dict(id=id,negative=negative,expected=expected,actual=evidence,status="PASS",grounds=grounds)
        except BaseException as e:
            record=dict(id=id,negative=negative,expected=expected,status="FAIL",error=repr(e),grounds=grounds)
        record["evidence_class"]="STATIC_GRAPH_OR_SYNTHETIC_UNIT_NOT_PHYSICAL_SIMULATION"
        results.append(record)
        print(id+" "+record["status"],flush=True)

    check("SCHEMA",False,"6 CDU; 12 secondary pumps; 18 racks; 72 rack valves; provenance and domain integrity",lambda:validate_schema(g),"R12 PID-005/006; S2设备清单")
    def steady(p,s):
        f=operating_fixture(g,p,s); proof=connectivity(g,f)
        assert not proof["isolation_errors"]
        assert all(u["primary_connected"] and all(r["connected"] for r in u["racks"]) for u in proof["units"])
        # No secondary fluid edge can reach any primary port.
        edges=enabled_edges(g,f["valves"],f["pumps"])
        assert path(edges,"G01-C01B:P2-HX-OUT","G01-C01B:P1-IN") is None
        return dict(command={"selection":f["CDU_IDENTITY"],"primary":p.value,"secondary":s.value},actual_valves=f["valves"],actual_pumps=f["pumps"],connectivity=proof)
    check("CASE01_CDU_A_PRIMARY_A_SECONDARY_A",False,"18 racks connected through A CDU on A primary",lambda:steady(P.A,S.A),"PID-005/006/009 M-A")
    check("CASE02_CDU_B_PRIMARY_A_SECONDARY_B",False,"18 racks connected through B CDU on A primary",lambda:steady(P.A,S.B),"阀位矩阵 A8:O8; PID-009 T-2")
    check("CASE03_CDU_B_PRIMARY_B_SECONDARY_B",False,"18 racks connected through B CDU on B primary",lambda:steady(P.B,S.B),"PID-005 selector independence; PID-009 M-B")
    def t2():
        c,inputs=t2_trace(g)
        assert c.state=="COMPLETED_UNIT_INTENT_ONLY",c.events[-1]
        assert all(x["command"]["primary_network"]=="A" and not x["command"]["LP_B_START_REQUESTED"] for x in c.events)
        assert all(not x["pumps"]["G01-LP-B"] and not x["valves"]["G01-LP-B-I"] for x in inputs)
        final=inputs[-1]; edges=enabled_edges(g,final["valves"],final["pumps"])
        assert path(edges,"G01-BT-B:BOTTOM_LOAD","G01-C01B:P1-IN") is None
        assert c.events[-1]["permissives"]["PRESSURE_MASTER_TRANSFER_VALID"]
        assert c.events[-1]["permissives"]["FLOW_ESTABLISHED_VALID"]
        return dict(inputs=inputs,events=c.events,B_tank_load_route="NO_ENABLED_ROUTE",B_tank_depletion_dynamic="NOT_SIMULATED")
    check("CASE04_T2_NO_B_TANK_AUTO_DISCHARGE",False,"A->B CDU handover, primary A retained, B load route disabled, master single",t2,"T-2 source registration, no invented tank simulation")
    def t1():
        f=source_fixture(g,"A","W1");o=observation(g,1);o.update(valves=f["valves"],pumps=f["pumps"],source_flow_m3_h=[330.,330.],source_return_temperature_C=[38.,38.])
        c=T1Controller(P.A,o["CDU_IDENTITY"],"D1","W1")
        assert c.complete(g,o,1,POLICY)
        good=copy.deepcopy(o);o["CDU_IDENTITY"][0]="C01B"
        assert not c.complete(g,o,1,POLICY)
        return dict(command={"source":"W1","primary":"A","CDU_change":False},actual=good,negative_changed_identity_refused=True)
    check("CASE05_T1_NO_CDU_IDENTITY_CHANGE",False,"source D1->W1 retains CDU identities and primary A",t1,"PID-009 T-1")
    def neg_t2(mutate):
        c,inputs=t2_trace(g,mutate)
        assert c.state!="COMPLETED_UNIT_INTENT_ONLY"
        assert not any(x["verdict"]=="UNIT_READY_NOT_DYNAMIC_READY" for x in c.events)
        return dict(inputs=inputs,events=c.events,blocked=True)
    def cross(o,t):
        o["valves"]["G01-C01B-P1-CV-BS"]=o["valves"]["G01-C01B-P1-CV-BR"]=True
    check("CASE06_PRIMARY_CROSS_CONNECT_REFUSED",True,"refuse primary A/B simultaneous pairs",lambda:neg_t2(cross),"PID-005 primary isolation never inherits secondary overlap permission")
    negatives=[("CASE07_TEMP_MATCH_REFUSED",lambda o,t:o.update(delta_T_K=[2.01,2.01]),"secondary deltaT<=2K"),
       ("NEG_PRESSURE_MATCH_REFUSED",lambda o,t:o.update(delta_p_kPa=[5.01,5.01]),"secondary deltap<=5kPa"),
       ("NEG_STABLE_5S_REFUSED",lambda o,t:o.update(delta_T_K=[3.,3.]) if t<3 else None,"5s stability cannot be asserted after only 4s"),
       ("NEG_MASTER_REVOKE_MISSING",lambda o,t:o.update(old_master_revoked=False),"old master actual revoke required"),
       ("NEG_TWO_MASTERS",lambda o,t:o.update(pressure_masters=["G01-C01A","G01-C01B"]),"one pressure master only"),
       ("NEG_NO_PRIMARY_FLOW",lambda o,t:o.update(new_primary_flow_m3_h=[0.,0.]),"no primary FT, no completion"),
       ("NEG_NO_SECONDARY_FLOW",lambda o,t:o.update(new_secondary_flow_m3_h=[0.,0.]),"no secondary FT, no completion"),
       ("NEG_ONE_RACK_STARVED",lambda o,t:o["rack_flow_m3_h"].__setitem__(3,[0.,0.]),"header or CDU total cannot prove each rack"),
       ("NEG_PRIMARY_NETWORK_AUTO_CHANGE",lambda o,t:o.update(primary_network="B"),"T2 cannot change primary identity"),
       ("NEG_PRIMARY_RETURN_MISMATCH",lambda o,t:o["valves"].update({"G01-C01B-P1-CV-AR":False,"G01-C01B-P1-CV-BR":True}),"no A supply/B return"),
       ("NEG_PUMP_STOP_PROOF_MISSING",lambda o,t:o.update(old_pump_speed_pct=[1.,0.]),"closed valve not zero speed proof"),
       ("NEG_OLD_ISOLATION_MISSING",lambda o,t:o["valves"].update({"G01-U1-R01-CV-AS":True}) if t>=6.5 else None,"no new master until old path closed"),
       ("NEG_FUTURE_RELEASE",lambda o,t:o.update(release_s=t+.01),"no future observation"),
       ("NEG_UNTRUSTED_PLANT_TRUTH",lambda o,t:o.update(provenance="HIDDEN_PLANT_TRUTH"),"not a released observation API"),
       ("NEG_CHANNEL_MISSING",lambda o,t:o.update(delta_T_K=[1.]),"two measured channels required"),
       ("NEG_RACK_OVER_TEMPERATURE",lambda o,t:o["rack_temperature_C"].__setitem__(3,[45.01,45.01]),"rack45C hard limit unchanged"),
       ("NEG_NONFINITE_FLOW",lambda o,t:o.update(new_primary_flow_m3_h=[float('nan'),110.]),"nonfinite measurement refused")]
    for id,mut,why in negatives:
        check(id,True,"completion refused",lambda m=mut:neg_t2(m),"PID-006 + explicit unit fixture: "+why)
    def source_stop_missing():
        c=RechargeController(g,P.A,P.B,"W1",POLICY);o=observation(g,0)
        o.update(source_pump_zero_speed_proofs={},running_tank_budget_permit=True)
        row=c.step(o,0);assert row["state"]=="WAIT_STOP_PROOF" and row["command"]["source_network"]=="A"
        return dict(command=row["command"],actual=o,result=row,connectivity=connectivity(g,o))
    check("CASE08_SOURCE_STOP_PROOF_MISSING",True,"no switch from valve closure alone",source_stop_missing,"PID-008 steps 1-4")
    def stuck(o,t):
        o["valves"]["G01-U1-R01-CV-BS"]=False
    check("CASE09_STUCK_VALVE_NO_FAKE_PATH",True,"command open/actual closed gives no rack path",lambda:neg_t2(stuck),"PID-006 real valve feedback, not command")
    check("CASE10_STALE_NO_READY",True,"stale measurement cannot complete",lambda:neg_t2(lambda o,t:o.update(sample_s=max(0,t-1))),"source freshness policy OPEN; .5s used only in explicit unit fixture")
    def timeout():
        c,inputs=t2_trace(g,lambda o,t:o.update(new_secondary_flow_m3_h=[0.,0.]),end=36)
        assert c.state=="OVERLAP_TIMEOUT_HOLD"
        return dict(inputs=inputs,events=c.events,blocked=True)
    check("NEG_OVERLAP_30S_REFUSED",True,"overlap timer expiry latches HOLD",timeout,"PID-006 overlap<=30s")
    def enum_check():
        try: operating_fixture(g,S.A,P.A)
        except TypeError: return dict(actual="TypeError",command="interchange enum types",blocked=True)
        raise AssertionError("enum confusion admitted")
    check("NEG_ENUM_INTERCHANGE",True,"types with the same letter are not interchangeable",enum_check,"R12-I01")
    def no_pump_filter():
        f=operating_fixture(g);c="G01-C01A"
        f["pumps"][c+"-P2-PM1"]=False
        proof=connectivity(g,f);assert not any(r["connected"] for r in proof["units"][0]["racks"])
        f["pumps"][c+"-P2-PM2"]=True
        assert all(r["connected"] for r in connectivity(g,f)["units"][0]["racks"])
        f["valves"][c+"-FILTER1-SERVICE"]=False
        assert not any(r["connected"] for r in connectivity(g,f)["units"][0]["racks"])
        return dict(command="duty lost -> standby; both filters unavailable -> no path",actual=f,connectivity=connectivity(g,f))
    check("NEG_NO_UNPUMPED_UNFILTERED_BYPASS",True,"12 distinct pumps, standby works, no disputed centreline edge",no_pump_filter,"PID-005 declared intent only; disputed drawn line UNRESOLVED")
    def heat():
        f=operating_fixture(g,P.A,S.B);proof=connectivity(g,f)
        rack_heat=[147.25]*18 # independent expected source row, not generated component sum
        assert sum(x["liquid_heat_kW"] for x in g["components"] if x["kind"]=="RACK_LOAD")==2650.5
        unit=[]
        for u in proof["units"]:
            assert u["primary_connected"] and all(r["connected"] for r in u["racks"])
            q=sum(rack_heat[:6]);unit.append(dict(CDU=u["CDU"],rack_liquid_kW=q,HX_secondary_removed_kW=q,HX_primary_received_kW=q,
                 closure_error_kW=q-q,primary_flow_fixture_m3_h=110,secondary_flow_fixture_m3_h=68.37,
                 temperatures="NOT_COMPUTED_NO_CALIBRATED_UA"))
        assert sum(x["HX_primary_received_kW"] for x in unit)==2650.5
        # A disconnected path carries zero assigned HX transfer, not zero rack load.
        return dict(command=f["CDU_IDENTITY"],actual=f,connectivity=proof,unit_interfaces=unit,
            group_liquid_heat_kW=2650.5,not_included="pump heat/storage/dynamic temperatures; no physical conservation claim",
            disconnected_interface={"rack_heat_input_kW":883.5,"HX_transfer_kW":0.,"unremoved_load_kW":883.5})
    check("FLOW_ENERGY_INTERFACE",False,"18*147.25=2650.5kW routed via three active B CDUs; no fluid mixing",heat,"S2复算 R01/R02 + basic algebra interface, not solved heat-transfer capacity")
    def recharge():
        c=RechargeController(g,P.A,P.B,"W1",POLICY);inputs=[]
        for i in range(6):
            f=source_fixture(g,"A" if i<2 else "B","W1",running=i>=3)
            if i==1:
                for k in list(f["valves"]):
                    if k.startswith("G01-SRC-") or k.startswith("G01-W1-CV-"): f["valves"][k]=False
            o=observation(g,i*.5);o.update(valves=f["valves"],pumps=f["pumps"],
                source_pump_zero_speed_proofs={f"G01-SP{p:02d}":i<3 for p in range(1,5)},
                running_tank_budget_permit=True,suction_liquid_permit=True,source_flow_m3_h=[330.,330.] if i>=3 else [0.,0.],
                source_return_temperature_C=[38.,38.] if i>=4 else [44.,44.],independent_target_reserve_proof=i>=5)
            inputs.append(o);c.step(o,i*.5)
        assert c.state=="TARGET_RESERVE_PROVEN_UNIT_FIXTURE_ONLY",c.history
        assert all(x["pumps"]["G01-LP-A"] and not x["pumps"]["G01-LP-B"] for x in inputs)
        assert not c.history[-1]["DUAL_RESERVE_READY"] and not c.history[-1]["SECOND_FAULT_QUALIFIED"]
        return dict(inputs=inputs,events=c.history,reserve_physics="NOT_SIMULATED",source_performance="NOT_OEM_VERIFIED")
    check("SHARED_SOURCE_RECHARGE_SEQUENCE",False,"stop -> isolate -> target -> restart -> flow -> cold return -> separate reserve proof",recharge,"PID-008; no RC, no 440 actual flow assumption")
    return results
