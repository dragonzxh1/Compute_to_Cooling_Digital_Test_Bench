"""Finite comparisons, registered before execution. No controller fault lookahead."""
from v0_2.tests.tools.memphis_failure_closure_v1.scenarios import candidate

def cases():
    out=[]
    def add(id,group,**changes):
        spec=candidate('D',**changes);spec['id']=id
        out.append(dict(id=id,group=group,kind='forward',parameters=spec))
    add('SOURCE_SAME_A','baseline')
    for volume in (1.,3.,5.):
        add('BUFFER_'+str(int(volume))+'M3','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=volume,
            neutral_hx_ua_w_k=4000000.,fault='A_LOAD_RESTRICTION')
    add('BUFFER_LOW_UA','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=1000000.,fault='A_LOAD_RESTRICTION')
    add('BUFFER_EXTRA_RESISTANCE','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=4000000.,neutral_resistance_factor=1.2,fault='A_LOAD_RESTRICTION')
    add('BUFFER_STUCK_TRANSFER','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=4000000.,fault='A_LOAD_RESTRICTION',load_valve_stuck=True)
    add('BUFFER_COMMON_LOAD_LOSS','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=4000000.,common_load_loss_at_s=60.)
    add('BUFFER_REJECT_FALSE_READY','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=4000000.,prelude_s=0,precool_sensor_stuck_low=True,false_ready_claim=True)
    add('BUFFER_5M3_DT05','hydraulic',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=4000000.,fault='A_LOAD_RESTRICTION',dt_s=.05)
    add('SOURCE_WARM_NO_PRELOOP','hydraulic',preconditioning_mode='NONE',prelude_s=0,capacity_scale=1.,source_speed_margin=0.,use_fast_sensor_channel=False,cold_fraction=.7,ua_w_k=220000.)
    for offload in (10.,20.):
        add('SHARED_'+str(int(offload))+'S','recovery_shared',shared_recharge=True,shared_charge_s=offload,shared_at_s=120.,seconds=1800.,restore_with_four_pumps=False)
    add('SHARED_NO_HEADROOM','recovery_shared',shared_recharge=True,shared_charge_s=10.,shared_at_s=120.,seconds=1800.,capacity_scale=1.,source_speed_margin=0.,restore_with_four_pumps=False)
    add('SHARED_HEADROOM_CANDIDATE','recovery_shared',shared_recharge=True,shared_charge_s=10.,shared_at_s=120.,seconds=1800.,capacity_scale=1.3,source_speed_margin=.10,restore_with_four_pumps=False)
    for capacity in (500.,1000.):
        add('INDEPENDENT_RC_'+str(int(capacity)),'recovery_rc',recharge='INDEPENDENT',independent_recharge=True,preconditioning_mode='C',backup_initial='WARM',seconds=1800.,rc_capacity_kW=capacity,restore_with_four_pumps=True)
    add('BUFFER_PLUS_RECHARGE','recovery_rc',architecture='NEUTRAL_BUFFER',neutral_buffer_m3=5.,neutral_hx_ua_w_k=4000000.,recharge='INDEPENDENT',independent_recharge=True,preconditioning_mode='C',backup_initial='WARM',seconds=1800.,rc_capacity_kW=1000.,restore_with_four_pumps=True)
    add('SECOND_SHARED_900','second_fault',shared_recharge=True,shared_charge_s=10.,shared_at_s=120.,seconds=1020.,second_fault_at_s=900.,restore_with_four_pumps=False)
    add('SECOND_RC1000_900','second_fault',recharge='INDEPENDENT',independent_recharge=True,preconditioning_mode='C',backup_initial='WARM',seconds=1020.,second_fault_at_s=900.,rc_capacity_kW=1000.,restore_with_four_pumps=True)
    for offload in (10.,20.):
        add('SHARED_DEPLETED_'+str(int(offload))+'S','recovery_depleted',shared_recharge=True,shared_charge_s=offload,shared_at_s=120.,seconds=1800.,backup_initial='WARM',restore_with_four_pumps=False)
    add('SECOND_SHARED_DEPLETED_900','recovery_depleted',shared_recharge=True,shared_charge_s=10.,shared_at_s=120.,seconds=1020.,backup_initial='WARM',second_fault_at_s=900.,restore_with_four_pumps=False)
    return out
