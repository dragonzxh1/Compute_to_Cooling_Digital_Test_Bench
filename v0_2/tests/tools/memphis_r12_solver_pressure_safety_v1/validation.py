"""Unmodified old algorithm reproduction, before any solver change."""
import json
import sys
import time
from pathlib import Path
import numpy as np
from ..memphis_r12_dynamic_hydraulic_v1 import campaign as old


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf8")


def inputs():
    root=Path(old.__file__).parent
    reg=json.loads((root/"registration.json").read_bytes())
    graph=json.loads((root/reg["topology_file"]).read_bytes())
    return graph, reg


def serial(v):
    if isinstance(v,np.ndarray): return v.tolist()
    if isinstance(v,np.generic): return v.item()
    if isinstance(v,(str,int,float,bool,type(None))): return v
    if isinstance(v,dict): return {str(k):serial(x) for k,x in v.items() if not callable(x)}
    if isinstance(v,(list,tuple)): return [serial(x) for x in v]
    return str(type(v))


def reproduce(out):
    out.mkdir()
    graph, reg=inputs(); results=[]; captured={}
    def trace(frame,event,arg):
        if event=="call":
            return trace if frame.f_code.co_name=="solve" and frame.f_code.co_filename.endswith("hydraulics.py") else None
        if event=="exception" and frame.f_code.co_name=="solve":
            loc=frame.f_locals
            if isinstance(arg[1],RuntimeError) and "HYDRAULIC_NONCONVERGENCE" in str(arg[1]):
                net=loc["self"]
                captured.update({k:serial(v) for k,v in loc.items() if k not in ("self","evaluate","find")})
                captured.update(nodes=net.names, port_index=net.port_index,
                    diagnostic=net.failure, algorithm="UNMODIFIED_OLD_SOLVE",
                    exception=str(arg[1]))
        return trace
    for case in reg["cases"][:4]:
        dest=out/case["id"]
        try:
            sys.settrace(trace)
            result,_=old.run_case(graph,reg,case,dest)
            results.append(result)
        except RuntimeError as exc:
            if case["id"]!="NEG_EARLY_DUTY_EXIT" or "HYDRAULIC_NONCONVERGENCE" not in str(exc): raise
            assert captured and abs(json.loads((dest/"numerical_failure.json").read_bytes())["t"]-13.5)<1e-8
            last=json.loads((dest/"trace.ndjson").read_text(encoding="utf8").splitlines()[-1])
            save(dest/"last_valid_step.json",last)
            save(dest/"rejected_trial_full_diagnostics.json",captured)
            results.append(dict(case=case,execution_status="INVALID",
                expected_reproduction=True, failure=captured["diagnostic"]))
        finally: sys.settrace(None)
    c=results[0]
    assert abs(c["complete_at"]-35.2)<1e-7
    assert abs(c["min_rack_flow_m3_h"]-11.62290356569)<1e-6
    assert abs(c["max_rack_inlet_C"]-39.61142002412)<1e-6
    assert abs(c["max_hx_inlet_gauge_difference_kPa"]-192.41233186268)<1e-6
    assert results[-1]["execution_status"]=="INVALID"
    save(out/"unchanged_reproduction.json",dict(status="REPRODUCED_NOT_FIXED",results=results))
    return dict(status="REPRODUCED_NOT_FIXED",results=results)


def execute(out, stage):
    if stage=="baseline": return reproduce(out)
    raise RuntimeError("PATCH_NOT_IMPLEMENTED")
