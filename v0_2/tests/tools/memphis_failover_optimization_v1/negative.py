"""Small causal/refusal witnesses; only remote verified worker imports this module."""
from dataclasses import replace
from .group_model.coordination import SourceObservation,Coordinator,ProjectProtection,SourcePLC,record
from .audit import need,source_ready,first_post_fault_cold,terminal_source_ready,source_change_cut

def run():
    count=0
    def denied(fn):
        nonlocal count
        try:fn()
        except (ValueError,RuntimeError,AssertionError,TypeError):count+=1;return
        raise ValueError('NEGATIVE_NOT_REFUSED')
    o=SourceObservation(0,100000000,'sample',0.,0.,'A','W1',0.,0.,False,True,False,41.,
        (314.0948,)*3+(321.44,),(314.0948,)*3+(321.44,),330/3600,None,44.,True,True)
    def exercise(obs):
        c=Coordinator(options={'strategy':'COORDINATED_B'});p=ProjectProtection()
        # First indication and one-second dwell, both actual released samples.
        for now in (100000000,1100000000):
            sample=replace(obs,sample_ns=now-100000000,release_ns=now,record_id=str(now))
            r=c.request(sample,p.evaluate(sample,now),now)
        return c,r
    c,r=exercise(o);need(c.needed_tank=='B' and r['load_tank']=='B','POSITIVE_MEASURED_TRANSFER');count+=1
    c=Coordinator(options={'strategy':'EARLY_TEMPERATURE','reserve_trigger_c':43.5})
    healthy=replace(o,w1_available=True);r=c.request(healthy,ProjectProtection().evaluate(healthy,100000000),100000000)
    need(r['load_tank']=='A' and not c.thermal_takeover_used,'PREFAULT_EARLY_TRIGGER');count+=1
    for tt in ((321.44,)*4,(314.0948,321.44,321.44,321.44)):
        c,r=exercise(replace(o,tank_B_tt_k=tt));need(c.needed_tank=='A' and r['load_tank']=='A','WARM_RESERVE_ACCEPTED');count+=1
    c,r=exercise(replace(o,w2_available=False));need(r['load_tank']=='A','UNAVAILABLE_BACKUP_ACCEPTED');count+=1
    stale=replace(o,sample_ns=0,release_ns=100000000)
    c=Coordinator(options={'strategy':'COORDINATED_B'});p=ProjectProtection()
    for now in (2_000_000_000,3_000_000_000):r=c.request(stale,p.evaluate(stale,now),now)
    need(r['load_tank']=='A','STALE_RESERVE_ACCEPTED');count+=1
    denied(lambda:ProjectProtection().evaluate(replace(o,release_ns=300000000),100000000))
    denied(lambda:exercise(replace(o,tank_B_tt_k=())))
    denied(lambda:exercise(replace(o,tank_B_tt_k=(float('nan'),)*4)))
    s=ProjectProtection().evaluate(o,100000000);c=Coordinator(options={'strategy':'COORDINATED_B'})
    denied(lambda:c.request(o,record(dict(measurement_id='wrong')),100000000))
    denied(lambda:SourcePLC().issue(dict(permission='wrong',observation_id=o.record_id),s,o,100000000))
    plc=SourcePLC();moving=replace(o,source_speed=.5,source_valve=1.)
    req=dict(permission=s['sha256'],observation_id=o.record_id,source_tank='A',source_path='W1',recharge_enable=False)
    plc.issue(req,s,o,100000000)
    denied(lambda:plc.issue(dict(req,source_path='W2'),s,moving,100000000))
    denied(lambda:SourcePLC().issue(dict(req,source_path='W2',recharge_enable=True),s,o,100000000))
    denied(lambda:source_change_cut(dict(source_supply_valve=1.,source_return_valve=1.,source_speed=0.),dict(source_speed=0.)))
    step=dict(start_ns=29_900_000_000,end_ns=30_000_000_000,source_available={'W1':True},source_path='W1',source_flow_m3_h=330.,source_return_k=314.1)
    need(first_post_fault_cold([step],30,330) is None,'PREFAULT_FALSE_COLD_RETURN');count+=1
    need(not source_ready(dict(step,source_flow_m3_h=326.194),330),'FLOW_REQUIREMENT_LOWERED');count+=1
    failed=dict(step,start_ns=35_000_000_000,end_ns=36_000_000_000,source_available={'W1':False})
    need(not terminal_source_ready([step,failed],330),'SECOND_FAILURE_HIDDEN');count+=1
    return dict(refusal_and_positive_witnesses=count,status='PASS',scope='NEW_PROJECT_PLANNING_NOT_FORMAL_M1')
