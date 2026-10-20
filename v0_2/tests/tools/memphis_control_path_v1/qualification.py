"""Offline exact-profile trials, never read by the online controller."""
import json
from .checks import save
from v0_2.tests.tools.memphis_topology_audit_v1.discharge import full_discharge

def samples(d,c,hot_c):
    values=[]
    for row in json.loads((d/'case/series.json').read_bytes()):
        t=row['time_ns']/1e9
        if t%300!=0 and t!=c['seconds']:continue
        profiles={n:row['tank_'+n+'_k'] for n in ('A','B')}
        trials=full_discharge(profiles,c,hot_c,d/('PROFILE_'+str(round(t)).zfill(5)+'_90S.csv'))
        verdicts={}
        for n in ('A','B'):
            cold=sum(x<=314.5948 for x in profiles[n])*15/len(profiles[n]);ts=[x for x in trials if x['tank']==n]
            verdicts[n]=dict(cold_m3=cold,research85='PASS' if all(x['status']=='PASS' for x in ts) else 'FAIL',
                conditional_customer70_and_rise='PASS' if cold>=10.5 and all(x['rise_K']<=.5 for x in ts) else 'FAIL',
                maximum_outlet_C=max(x['maximum_outlet_C'] for x in ts),maximum_rise_K=max(x['rise_K'] for x in ts))
        values.append(dict(time_s=t,verdicts=verdicts,trials=trials))
    first={}
    for key in ('research85','conditional_customer70_and_rise'):
        first[key]={n:next((x['time_s'] for x in values if x['time_s']>c['fault_at_s'] and x['verdicts'][n][key]=='PASS'),None) for n in ('A','B')}
        first[key]['joint']=next((x['time_s'] for x in values if x['time_s']>c['fault_at_s'] and all(x['verdicts'][n][key]=='PASS' for n in ('A','B'))),None)
    result=dict(samples=values,first_tested=first,sampling='FIXED300S_AND_FINAL; not earliest continuous time or monotonic readiness',
        cold_definition='Research41.4448C; customer70 comparison is fraction+rise only, not inherited complete qualification',controller_feedback=False)
    save(d/'per_tank_qualification.json',result)
    return result
