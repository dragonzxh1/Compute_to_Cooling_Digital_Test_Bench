"""Bounded A-L mathematical controls, then four original 60 s regressions."""
import copy
import json
import math
import time
from pathlib import Path
import numpy as np
from .validation import inputs,save
from .constrained import mixed_solve,FORWARD
from .audited import Plant,PressureController
from ..memphis_r12_dynamic_hydraulic_v1 import campaign


def edge(name,i,j,kind,k,head=0.):
    return dict(id=name,tag=name,i=i,j=j,kind=kind,k=k,head=head)


def trial(label,heads,load_k=2e8,seed=1e-3):
    # Two independent pump/check legs in parallel, one common passive return.
    edges=[edge("P1",0,1,"pump",1e8,heads[0]),edge("CK1",1,3,"check_valve",1e6),
        edge("P2",0,2,"pump",1e8,heads[1]),edge("CK2",2,3,"check_valve",1e6),
        edge("LOAD",3,0,"rack",load_k)]
    result,metrics=mixed_solve(4,edges,[0],.02,1e5,.1,np.zeros(4),np.full(5,seed))
    return dict(test=label,heads_Pa=heads,load_K=load_k,metrics=metrics,
        flows_m3_s=result[1].tolist() if result is not None else None,
        expected="CONVERGED_WITH_NO_FORWARD_VIOLATION",
        test_pass=result is not None and not metrics["physical_violation"])


def mathematics(out):
    out.mkdir();records=[]
    definitions=[
        ("A_NORMAL",[(300000.,0.)]),
        ("B_RAMP_TO_ZERO",[(300000*x*x,0.) for x in (1.,.5,.1,.01,0.)]),
        ("C_CHECK_CLOSE",[(300000.,300000.),(100.,300000.),(0.,300000.)]),
        ("D_STANDBY_BUILD",[(300000.,x) for x in (0.,100.,10000.,300000.)]),
        ("E_TWO_PARALLEL",[(300000.,300000.)]),
        ("F_MASTER_HANDOVER",[(300000.,100000.),(200000.,200000.),(100000.,300000.)]),
        ("G_EARLY_EXIT",[(300000.,100.),(100.,100.),(0.,100.)]),
        ("H_NO_STANDBY_FLOW",[(0.,0.)]),
        ("I_REVERSE_CHECK_PRESSURE",[(1.,300000.)]),
        ("J_NEAR_ZERO_GUESS",[(300000.,100.)])]
    for label,pairs in definitions:
        for j,pair in enumerate(pairs):
            records.append(trial(label+"/"+str(j),pair,seed=1e-14 if label.startswith("J_") else .001))
    for factor in (.1,1.,10.):
        records.append(trial("K_RESISTANCE_SLOPE/"+str(factor),(200000.,300000.),load_k=2e8*factor))
    _,m=mixed_solve(2,[edge("CV",0,1,"check_valve",1e6)],[0],.02,1e5,.1,np.zeros(2),np.zeros(1),demand=np.array([.001,0.]))
    records.append(dict(test="L_NO_SOURCE_FOR_PRESCRIBED_NET_OUTFLOW",metrics=m,
        expected="PHYSICAL_INFEASIBLE",test_pass=m["status"]=="PHYSICAL_INFEASIBLE"))
    # Freeze the actually rejected historical trial, including its poor initial
    # iterate, and require an independent simultaneous KCL/complementarity solve.
    frozen=json.loads((Path(__file__).parent/"inputs/historical_rejected_trial.json").read_bytes())["secondary"]
    save(out/"tests_before_saved_state.json",records)
    graph,reg=inputs();plant=Plant(graph,reg,reg["cases"][0]);net=plant.sec
    edges=frozen["active_edges"];parents=list(range(len(net.names)))
    def find(i):
        while parents[i]!=i:i=parents[i]
        return i
    for e in edges:parents[find(e["j"])]=find(e["i"])
    zones={}
    for i in range(len(net.names)):zones.setdefault(find(i),[]).append(i)
    preferred=[net.node(f"G01-C01{s}-P2-XV-RET:OUT") for s in "AB"]
    anchors=[next((i for i in preferred if i in z),min(z)) for z in zones.values()]
    p=np.array(frozen["scaled_pressures"]);q=np.array([e["flow"] for e in edges])
    before=np.zeros(len(net.names));jac=np.zeros((len(net.names),len(net.names)))
    recomputed=[]
    for e in edges:
        dp=(p[e["i"]]-p[e["j"]])*1e5;h=dp+e["head"];k=e["k"];regp=.1
        if e["kind"] in FORWARD:
            value=math.sqrt(h/k) if h>0 else 0.
            der=.5/math.sqrt(k*max(h,regp)) if h>0 else 0.
        else:
            value=dp/(math.sqrt(k)*(dp*dp+regp*regp)**.25)
            der=(.5*dp*dp+regp*regp)/(math.sqrt(k)*(dp*dp+regp*regp)**1.25)
        recomputed.append(value);i,j=e["i"],e["j"];before[i]+=value/net.qd;before[j]-=value/net.qd
        d=der*1e5/net.qd;jac[i,i]+=d;jac[j,j]+=d;jac[i,j]-=d;jac[j,i]-=d
    assert abs(max(abs(before))-.033574007252778475)<1e-8
    solution,metrics=mixed_solve(len(net.names),edges,anchors,net.qd,1e5,.1,p,q)
    save(out/"historical_rejected_trial_recalculation.json",dict(
        original_KCL_max=float(max(abs(before))),original_flow_recomputed=recomputed,
        original_residual_vector=before.tolist(),original_jacobian=jac.tolist(),nodes=net.names,
        pump_speeds_derived=[dict(tag=e["tag"],speed=math.sqrt(e["head"]/reg["assumptions"]["pump_shutoff_head_Pa"]))
            for e in edges if e["kind"]=="pump"],
        new_metrics=metrics,new_flows=solution[1].tolist() if solution is not None else None))
    records.append(dict(test="G_SAVED_REJECTED_STATE",metrics=metrics,
        expected="CONVERGED",test_pass=solution is not None and not metrics["physical_violation"]))
    save(out/"tests.json",records)
    if not all(r["test_pass"] for r in records):raise RuntimeError("MATHEMATICAL_GATE_FAILED")
    return records


def run(out):
    out.mkdir();records=mathematics(out/"math")
    graph,reg=inputs();results=[]
    old_plant=campaign.Plant;old_control=campaign.Controller
    try:
        campaign.Plant=Plant
        for case in reg["cases"][:4]:
            print("BEGIN MCP "+case["id"],flush=True)
            r,_=campaign.run_case(graph,reg,case,out/case["id"])
            r["interpretation"]="NUMERICAL_REGRESSION_WITH_ORIGINAL_RESEARCH_PARAMETERS_NOT_00_01_DESIGN_VALIDATION"
            results.append(r)
            print("END MCP "+case["id"],flush=True)
        campaign.Controller=PressureController
        case=copy.deepcopy(reg["cases"][0]);case["id"]="PRESSURE_PROTECTED_COLD"
        r,_=campaign.run_case(graph,reg,case,out/case["id"]);results.append(r)
    finally:campaign.Plant=old_plant;campaign.Controller=old_control
    save(out/"suite_summary.json",dict(math=records,results=results,
        scope="MATHEMATICAL_AND_ORIGINAL_MODEL_COMPARISON_ONLY",final_design_validation="NOT_PERFORMED",
        engineering_status="MEMPHIS_ENGINEERING_NOT_APPROVED"))
    return dict(mathematical_subcases=len(records),results=results)
