import json
from pathlib import Path
from v0_2.tests.tools.gb300_m1_closed_loop_v1.simulation import write, read
from v0_2.tests.tools.gb300_m1_closed_loop_v1.plant import check
from v0_2.thermal.provenance import ParameterRecord

HERE=Path(__file__).resolve().parent
REG=read(HERE/'registration.json')
PROJECT=read(HERE/'upstream/project.json')
P={x['id']:x for x in PROJECT['parameters']}
RHO=REG['six_rack']['rho_kg_m3'];CP=REG['six_rack']['cp_j_kg_k'];CV=RHO*CP;G=9.80665

def p(name,value,unit):
    return ParameterRecord(name,value,unit,'ENGINEERING_ASSUMPTION',
        'memphis_project_v1/registration.json; document budgets/synthetic curves, NOT OEM',
        0.,'2026-10-17',(value,value),'CALIBRATION_REQUIRED')

def case_by_id(name):
    return next(x for x in REG['cases'] if x['id']==name)

def rounding_bound(*terms,operations=256):
    from math import fsum
    u=2**-53;gamma=operations*u/(1-operations*u)
    return gamma*max(1.,fsum(abs(x) for x in terms))
