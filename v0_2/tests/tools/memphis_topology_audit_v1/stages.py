"""New remote-only audit stages, not a new customer plant implementation."""
import ast,json,gc
from pathlib import Path
from v0_2.tests.tools.memphis_hydraulic_continuity_v1.checks import save,digest,require,evaluate
HERE=Path(__file__).resolve().parent

def stage(entry,directory):
    if entry['kind']=='assertions':
        for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
        from .verify import assertions
        from .topology import build,check_graph
        graph=build();proof=check_graph(graph)
        return dict(kind='independent_FV_negative_and_netlist_checks',equations=assertions(),netlist=proof)
    if entry['kind']=='final':
        from .report import finalize
        return finalize(directory)
    from v0_2.tests.tools.memphis_hydraulic_continuity_v1 import simulation
    from .observer import ObserverPlant
    binding=json.loads((HERE/'baseline_binding.json').read_bytes())
    spec=dict(binding['case']['parameters']);spec.update(entry['change'])
    if entry['id']!='BASELINE_EXACT':spec['id']=entry['id']
    save(directory/'case_spec.json',spec)
    plant=[]
    original=simulation.SourcePlant
    def factory(c):
        p=ObserverPlant(c,directory);plant.append(p);return p
    simulation.SourcePlant=factory
    try:simulation.run(spec,directory/'case')
    finally:
        simulation.SourcePlant=original
        summary=plant[0].finish() if plant else None
    result=evaluate(directory/'case',spec)
    if entry['id']=='BASELINE_EXACT':
        require(result['raw_sha256']==binding['case']['raw_sha256'],'OBSERVATION_CHANGED_HISTORICAL_SIX_RAW_FILES')
        require(result['events']==binding['case']['events'],'BASELINE_EVENT_DRIFT')
    summary.update(id=entry['id'],parameters=spec,raw_sha256=result['raw_sha256'],baseline_exact_six_hashes=entry['id']=='BASELINE_EXACT',
        final_challenge=result['reserve_challenge'],grades=result['grades'],maximum_inlet_C=result['maximum_inlet_C'],
        minimum_load_m3_h=result['minimum_load_m3_h'],second_fault=result['second_fault'],events=result['events'],
        source_commit=__import__('os').environ['GITHUB_SHA'],independent_global=result['independent'])
    save(directory/'audit_summary.json',summary)
    # Controller observations are reconstructed only from already-released source frames.
    frames=json.loads((directory/'case/source_phases.json').read_bytes());timeline=[]
    done=next((e['time_ns'] for e in result['events'] if e['from_state']=='STOP_RECHARGE' and e['to_state']=='RUN' and e['reason']=='RC_ZERO_SPEED_AND_ESTIMATED_RESERVE'),None)
    for f in frames:
        o=f['measurement'];now=f['time_ns'];est={}
        for name in ('A','B'):
            tt=o['reserve_'+name+'_k']
            est[name]=sum(a+.2<=314.5948 and b+.2<=314.5948 for a,b in zip(tt,tt[1:]))*15/16
        timeline.append(dict(time_s=now/1e9,sample_ns=o['sample_ns'],release_ns=o['release_ns'],measurement_id=o['record_id'],
            state=f['request']['coordinator_state'],estimated_A_m3=est['A'],estimated_B_m3=est['B'],
            B_RECHARGE_DONE=done is not None and now>=done,
            B_RECHARGE_DONE_semantics='ACTUAL_EXISTING_STOP_RECHARGE_TO_RUN_EVENT; B_ESTIMATE_ONLY',
            A_inventory_gate_estimated=est['A']>=12.75,DUAL_inventory_gate_estimated=min(est.values())>=12.75,
            A_RESERVE_READY='NOT_A_REAL_90S_READY_SIGNAL',DUAL_RESERVE_READY='NOT_IMPLEMENTED_IN_ORIGINAL_CONTROLLER',
            SECOND_FAULT_QUALIFIED='NOT_A_CONTROLLER_SIGNAL; requires independent full-system test',
            control_input='ACTUALLY_RELEASED_17TT_ONLY; not future raw profiles'))
    save(directory/'09_RECHARGE_CONTROL_TIMELINE.json',timeline)
    gc.collect()
    print('TOPOLOGY_AUDIT_ACTUAL '+entry['id']+' '+str(result['grades']),flush=True)
    return dict(kind='fresh_observational_CV_audit',case_id=entry['id'],baseline_exact_six_hashes=summary['baseline_exact_six_hashes'],
        steps=summary['steps'],max_CV_step_residual_J=summary['max_CV_step_residual_J'],grades=result['grades'])
