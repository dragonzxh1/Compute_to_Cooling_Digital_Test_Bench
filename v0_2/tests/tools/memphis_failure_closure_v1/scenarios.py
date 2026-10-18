"""Finite versioned registry expansion; all expanded inputs saved before model runs."""
def legacy(**changes):
    c=dict(scope='GROUP18',ua_w_k=220000.,dt_s=.1,seconds=240.,source_variant='V9',tank_kind='STRATIFIED',fault='W1_LOSS',fault_at_s=30.,recharge_at_s=120.,layers=80,cold_fraction=.85,standby_initial_c=40.5,startup_s=20.)
    c.update(changes);return c
def candidate(name,**changes):
    c=legacy(extensions=True,ua_w_k=240000.,cold_fraction=.9,cold_initial_c=40.5,secondary_initial_c=43.8,primary_target_c=40.7,
        preconditioning_mode='A',precool_flow_m3_h=90.,precool_capacity_kW=100.,precool_floor_c=40.5,prelude_s=1200,
        pipe_ambient_UA_W_K=500.,tank_ambient_UA_W_K=50.,ready_flow_m3_h=90.,use_fast_sensor_channel=False)
    if name=='A':c.update(preconditioning_mode='NONE',prelude_s=0,cold_fraction=.85)
    if name=='B':c.update(cold_fraction=.85)
    if name in ('D','E'):c.update(capacity_scale=1.15,source_speed_margin=.03,use_spare=True,use_fast_sensor_channel=True,design_flow_takeover=True)
    if name=='E':c.update(third_source=True,preconditioning_mode='C',tank_volume_m3=20.)
    c.update(changes);return c
def trials(study):
    out=[]
    def add(name,c):out.append(dict(c,id=study+'__'+name))
    if study=='smoke':add('D_nominal',candidate('D'))
    elif study.startswith('cause_'):
        axis=study[6:];axes={'capacity':dict(capacity_scale=.8),'pump':dict(source_head_factor=.97),'measurement':dict(sensor_delay_s=1.2),'second':dict(second_source_failure=True),
            'joint':dict(wet_bulb_c=32.,capacity_scale=.8,cold_initial_c=41.2,standby_initial_c=42.,mixing_m3_s=.001,source_head_factor=.97,primary_efficiency=.6,valve_s=10.,sensor_bias_K=-.2,sensor_delay_s=.4)}
        for volume in (15.,20.):
            add('original'+str(int(volume)),legacy(tank_volume_m3=volume,**axes[axis]));fixed=dict(axes[axis])
            fixed.update({'capacity':dict(capacity_scale=1.),'pump':dict(source_head_factor=1.),'measurement':dict(sensor_delay_s=.4),'second':dict(second_source_failure=False),'joint':dict(source_head_factor=1.)}[axis])
            add('single_counterfactual'+str(int(volume)),legacy(tank_volume_m3=volume,**fixed))
            modified=dict(axes[axis])
            if 'capacity_scale' in modified:modified['capacity_scale']*=1.15
            add('physical_modified'+str(int(volume)),candidate('E' if axis=='second' else 'D',tank_volume_m3=volume,**modified))
    elif study.startswith('option_'):add('nominal',candidate(study[-1]))
    elif study.startswith('robust_'):
        name=study[-1];mods=[{},dict(wet_bulb_c=32.),dict(capacity_multiplier=.8),dict(cold_initial_c=41.2),dict(preconditioning_loss_at_s=0),dict(mixing_m3_s=.005,short_circuit=.05),
            dict(source_head_factor=.97),dict(primary_efficiency=.6),dict(valve_s=10.,valve_response_deadline_s=12),dict(sensor_bias_K=-.2),dict(sensor_bias_K=.2,sensor_delay_s=.4),dict(sensor_delay_s=1.2),
            dict(second_source_failure=True),dict(fault='A_LOAD_RESTRICTION',load_valve_stuck=True),dict(layers=160),dict(layers=160,dt_s=.05),
            dict(wet_bulb_c=32.,capacity_multiplier=.8,cold_initial_c=41.2,mixing_m3_s=.001,source_head_factor=.97,primary_efficiency=.6,valve_s=10.,valve_response_deadline_s=12,sensor_bias_K=-.2,sensor_delay_s=.4)]
        for i,m in enumerate(mods):
            c=candidate(name,**m);c['capacity_scale']=c.get('capacity_scale',1.)*c.pop('capacity_multiplier',1.);add(f'{i:02}',c)
    elif study=='topologies':
        for mode in ('A','C'):add(mode,candidate('D',preconditioning_mode=mode))
        add('precool_loss',candidate('D',preconditioning_loss_at_s=0))
    elif study=='asymmetric':
        add('A85_B90',candidate('D',cold_fraction_A=.85,cold_fraction_B=.9))
        add('A90_B85',candidate('D',cold_fraction_A=.9,cold_fraction_B=.85))
        add('smeared',candidate('D',initial_profile='SMEARED'))
    elif study=='readiness_negatives':
        for label,change in [('near_TT_stuck',dict(prelude_s=0,precool_sensor_stuck_low=True,false_ready_claim=True)),('expired',dict(ready_extra_age_s=2.,false_ready_claim=True)),
            ('fake_source_ready',dict(preconditioning_mode='NONE',prelude_s=0,false_ready_claim=True)),('rewarmed_deadleg',dict(deadleg_m3=.25,deadleg_open_at_s=80)),('fast_sensor_power_loss',dict(sensor_delay_s=1.2,fast_channel_failed=True))]:add(label,candidate('D',**change))
    elif study=='modules':
        for scale in (1.,1.05,1.15,1.25):
            c=candidate('D',module_loss=True,capacity_scale=scale,design_flow_takeover=False);c.pop('fault');add(str(scale),c)
        c=candidate('D',module_loss=True,capacity_scale=1.15,source_speed_margin=.15,design_flow_takeover=False);c.pop('fault');add('remaining4_V9_margin15pct',c)
        c=candidate('D',module_loss=True,capacity_scale=1.15,source_speed_margin=.15,source_variant='PID',design_flow_takeover=False);c.pop('fault');add('remaining4_R10_maxspeed',c)
        c=candidate('D',module_loss=True);c.pop('fault');add('measured_design_flow_takeover',c)
    elif study=='pumps':
        for margin in (0.,.0154,.03):add('H0minus3_margin'+str(margin),candidate('D',source_head_factor=.97,source_speed_margin=margin))
        add('R10_minus3',candidate('D',source_variant='PID',source_head_factor=.97))
        add('pump_out_no_spare',candidate('D',pump_loss_at_s=40,use_spare=False));add('pump_out_spare',candidate('D',pump_loss_at_s=40,use_spare=True))
    elif study=='valves':
        add('A_demand_no_stuck',candidate('D',fault='A_LOAD_RESTRICTION'))
        add('A_demand_stuck',candidate('D',fault='A_LOAD_RESTRICTION',load_valve_stuck=True))
        add('source_stuck',candidate('D',source_valve_stuck=True))
        add('false_open_feedback',candidate('D',valve_feedback_lie=True))
    elif study=='common':
        add('two_sources_D',candidate('D',second_source_failure=True));add('third_E',candidate('E',second_source_failure=True))
        add('source_header_E',candidate('E',common_source_loss_at_s=60))
        add('load_header_E',candidate('E',common_load_loss_at_s=60))
    elif study=='recharge_old':
        for dp in (120.,115.82):
            c=legacy(recharge='INDEPENDENT',backup_initial='WARM',seconds=600.,source_variant='PID',recharge_dp_kpa=dp);c.pop('fault');add(str(dp),c)
    elif study=='recharge_new':
        for cap in (500.,1000.):add(str(cap),candidate('D',recharge='INDEPENDENT',independent_recharge=True,preconditioning_mode='C',backup_initial='WARM',seconds=600.,rc_capacity_kW=cap,restore_with_four_pumps=True))
    else:raise ValueError('UNREGISTERED_STUDY '+study)
    return out
