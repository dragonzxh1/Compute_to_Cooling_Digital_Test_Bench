"""Independent analytic auditor: NO imports from the simulation/plant/solver.

Reconstructs declared quadratic hydraulics, HX, pump loss partition and all
eight liquid control-volume updates from persisted traces. Numerical closure
is not calibration or validation of the physical assumptions themselves.
"""
import json
from math import exp, fsum, isfinite, sqrt
from pathlib import Path


def require(ok, reason):
    if not ok: raise ValueError(reason)


def read(path):
    return json.loads(Path(path).read_bytes())


def rounding_bound(*terms, operations=128):
    u = 2**-53
    gamma = operations*u/(1-operations*u)
    return gamma*max(fsum(abs(x) for x in terms), 1.)


def audit(directory, spec):
    directory = Path(directory)
    inp = read(directory/'input.json'); c = inp['config']
    series = read(directory/'series.json'); phases = read(directory/'phases.json')
    physics = read(directory/'physics_intervals.json'); measurements = read(directory/'measurements.json')
    outcome = read(directory/'result.json')
    bytime = {r['time_ns']:r for r in series}
    byid = {r['measurement_record_id']:r for r in measurements}
    setting, fault = spec['setting'], spec.get('fault')
    rho, cp = c['density_kg_m3'], c['cp_j_kg_k']; cv = rho*cp
    volumes = [c['secondary_supply_volume_m3'],*([c['rack_fluid_volume_each_m3']]*6),c['secondary_return_volume_m3']]
    capacities = [v*cv for v in volumes]
    qd, dpd, nd = c['design_secondary_flow_m3_s'],c['design_secondary_dp_pa'],c['design_speed']
    resistance = dpd/qd**2
    kcurve = resistance*(c['quadratic_shutoff_factor']-1)
    h0 = dpd*c['quadratic_shutoff_factor']/nd**2*setting['pump_head_scale']
    def multiplier(now):
        return 100. if fault and fault['kind']=='NETWORK_RESISTANCE_100X' and now>=fault['start_ns'] else 1.
    def hydraulic(speed, now):
        q = sqrt(h0*speed**2/(resistance*multiplier(now)+kcurve))
        return q, h0*speed**2-kcurve*q**2
    def temperatures(r):
        return [r['supply_k'],*r['rack_return_k'],r['return_k']]
    max_node_residual = max_hydraulic_error = 0.
    sums = dict(it_j=0.,liquid_j=0.,air_j=0.,pump_electrical_j=0.,pump_liquid_j=0.,pump_ambient_j=0.,hx_j=0.)
    source_cursor = 0
    for p in physics:
        a,b = bytime[p['start_ns']],bytime[p['end_ns']]
        dt = (p['end_ns']-p['start_ns'])/1e9
        # New network event at b happens AFTER old interval advancement.
        q,head = hydraulic(b['actual_speed'],p['start_ns'])
        old,new = temperatures(a),temperatures(b)
        ts,*rest = old; racks,ret = rest[:6],rest[-1]
        cs,primary_c = cv*q, cv*c['primary_flow_m3_s']
        small,large = min(cs,primary_c),max(cs,primary_c)
        cr=small/large; ntu=c['hx_ua_w_k']/small
        if abs(1-cr)<1e-10: effectiveness=ntu/(1+ntu)
        else:
            e=exp(-ntu*(1-cr)); effectiveness=(1-e)/(1-cr*e)
        hx=effectiveness*small*(ret-c['primary_inlet_k'])
        require(abs(hx-p['hx_to_primary_w'])<=rounding_bound(hx,p['hx_to_primary_w']), 'INDEPENDENT_HX_FORMULA')
        primary_gain=primary_c*(p['primary_outlet_k']-c['primary_inlet_k'])
        require(abs(primary_gain-hx)<=rounding_bound(primary_c*p['primary_outlet_k'],primary_c*c['primary_inlet_k'],hx), 'PRIMARY_SECONDARY_HX_OWNERSHIP')
        hyd=head*q; shaft=hyd/.75; motor_in=shaft/.8; electrical=motor_in/.9
        liquid_pump=hyd+(shaft-hyd)+.5*(motor_in-shaft)
        ambient_pump=(electrical-motor_in)+.5*(motor_in-shaft)
        require(abs(electrical-p['pump_electrical_w'])<=rounding_bound(electrical,p['pump_electrical_w']), 'INDEPENDENT_PUMP_POWER')
        while source_cursor+1<len(c['load_profile']) and c['load_profile'][source_cursor+1]['time_ns']<=p['start_ns']:
            source_cursor+=1
        loads=c['load_profile'][source_cursor]['rack_it_w']
        require(loads==p['rack_it_w'], 'INDEPENDENT_SOURCE_OWNERSHIP_OR_TIME')
        liquid=[x*c['liquid_fraction'] for x in loads]
        require(liquid==p['liquid_heat_w'], 'LIQUID_HEAT_FRACTION')
        series_k=resistance*c['series_resistance_fraction']/2*multiplier(p['start_ns'])
        branch_k=resistance*(1-c['series_resistance_fraction'])*36*multiplier(p['start_ns'])
        branch_hyd=branch_k*(q/6)**3
        # Independent nodal divergence: advection cancels globally. Hydraulic
        # work dissipates on passive edges, NEVER again at the pump receiver.
        rates=[cv*q*(ret-ts)-hx+series_k*q**3]
        rates += [cv*q/6*(ts-t)+w+branch_hyd for t,w in zip(racks,liquid)]
        rates += [fsum(cv*q/6*(t-ret) for t in racks)+(liquid_pump-hyd)+series_k*q**3]
        for j in range(8):
            error=(new[j]-old[j])*capacities[j]-dt*rates[j]
            require(abs(error)<=rounding_bound(old[j]*capacities[j],new[j]*capacities[j],dt*rates[j]), 'LOCAL_CONTROL_VOLUME_ENERGY')
            max_node_residual=max(max_node_residual,abs(error))
        rates_out=dict(it_j=fsum(loads),liquid_j=fsum(liquid),air_j=fsum(loads)-fsum(liquid),
            pump_electrical_j=electrical,pump_liquid_j=liquid_pump,pump_ambient_j=ambient_pump,hx_j=hx)
        for key,value in rates_out.items(): sums[key]+=value*dt
    max_mass_residual=0.
    for r in series:
        q,head=hydraulic(r['actual_speed'],r['time_ns'])
        require(abs(q-r['flow_m3_s'])<=rounding_bound(q,r['flow_m3_s']), 'FLOW_NOT_ACTUAL_SPEED_DRIVEN')
        require(abs(head-r['dp_pa'])<=rounding_bound(head,r['dp_pa']), 'DP_NOT_ACTUAL_SPEED_DRIVEN')
        require(len(r['branch_flows_m3_s'])==6, 'EXACT_SIX_BRANCHES')
        mass=rho*(fsum(r['branch_flows_m3_s'])-r['flow_m3_s'])
        require(abs(mass)<=rounding_bound(rho*r['flow_m3_s']), 'INDEPENDENT_NODE_MASS_BALANCE')
        max_mass_residual=max(max_mass_residual,abs(mass)); max_hydraulic_error=max(max_hydraulic_error,abs(head-r['dp_pa']))
    seen=set(); repeats=0; previous=None; fault_since=None
    for f in phases:
        m=f['PRE']['measurement']; source=byid[m['measurement_record_id']]
        require(m['sample_ns']<=m['release_ns']<=f['time_ns'], 'MEASUREMENT_FUTURE_ACCESS')
        valid=source['quality']=='VALID' and f['time_ns']-source['sample_ns']<=c['sensor_max_age_ns']
        require((m['quality']=='VALID')==valid, 'STALE_OBSERVATION_RELABELED_FRESH')
        if valid:
            actual=bytime[source['sample_ns']]
            require(m['measured_speed']==source['pump_speed']==actual['actual_speed'], 'MEASUREMENT_SOURCE')
            expected=min(.9,max(.3,c['initial_speed']+c['feedback_gain_fraction_per_k']*(max(source['rack_return_k'])-c['return_target_k'])))
            require(expected==f['controller_request'], 'CONTROLLER_FUTURE_OR_TRUTH_LEAK')
        else:
            require(f['controller_request'] is None and m['measured_speed'] is None, 'INVALID_SENSOR_TRUTH_FALLBACK')
        if m['measurement_record_id'] in seen: repeats+=1
        seen.add(m['measurement_record_id'])
        pre,safety,plc,post=f['PRE'],f['SAFETY'],f['PLC'],f['POST']
        if previous:
            require(pre['old_command']['value']==previous['command'] and pre['old_command']['issue_ns']==previous['issue_ns'], 'PRE_NEW_COMMAND_ACCESS')
        require(safety['pre_digest']==f['immutable_pre_digest'] and plc['safety_digest']==f['immutable_safety_digest'], 'IMMUTABLE_PHASE_BINDING')
        require(post['pre_id']==pre['record_id'] and post['plc_id']==plc['record_id'] and plc['safety_id']==safety['record_id'], 'PLC_POST_BINDING')
        require(f['actuator_command']['producer_module']=='PLC' and f['envelope']['minimum_speed']<=plc['command']<=f['envelope']['maximum_speed'], 'PLC_OWNERSHIP_OR_RESTRICTION')
        if safety['severity']=='FAULT' and fault_since is None: fault_since=f['time_ns']
        if fault_since is not None: require(safety['severity']=='FAULT', 'FAULT_AUTO_RESET')
        previous=plc
    stored=fsum((b-a)*cap for a,b,cap in zip(temperatures(series[0]),temperatures(series[-1]),capacities))
    residual=stored-sums['liquid_j']-sums['pump_liquid_j']+sums['hx_j']
    bound=outcome['ledger']['roundoff_bound_j']
    require(abs(residual)<=bound, 'INDEPENDENT_TOTAL_FLUID_ENERGY')
    last=series[-1]; first_tail=bytime[c['duration_ns']-10_000_000_000]
    volume_mass=rho*fsum(volumes)
    def first(condition):
        return next((f['time_ns']/1e9 for f in phases if condition(f)),None)
    snapshots=[]
    for seconds in (0,10,30,60,90,120):
        r=bytime[seconds*10**9]
        snapshots.append(dict(time_s=seconds,supply_c=r['supply_k']-273.15,return_c=r['return_k']-273.15,
            max_rack_return_c=max(r['rack_return_k'])-273.15,flow_m3_h=r['flow_m3_s']*3600,
            dp_kpa=r['dp_pa']/1000,command=r['commanded_speed'],actual=r['actual_speed'],safety=r['safety']))
    return dict(status='INDEPENDENT_DECLARED_EQUATIONS_PASS',step_count=len(physics),phase_count=len(phases),
        unique_sources=len(seen),repeated_observations=repeats,max_local_energy_residual_j=max_node_residual,
        total_fluid_energy_residual_j=residual,energy_bound_j=bound,independent_integrals=sums,
        secondary_mass_initial_kg=volume_mass,secondary_mass_final_kg=volume_mass,
        max_node_mass_residual_kg_s=max_mass_residual,max_hydraulic_error_pa=max_hydraulic_error,
        final_supply_c=last['supply_k']-273.15,final_return_c=last['return_k']-273.15,
        max_supply_c=max(r['supply_k'] for r in series)-273.15,
        max_rack_return_c=max(max(r['rack_return_k']) for r in series)-273.15,
        final_flow_m3_h=last['flow_m3_s']*3600,final_dp_kpa=last['dp_pa']/1000,
        final_actual_speed=last['actual_speed'],final_command=last['commanded_speed'],
        stored_change_mj=stored/1e6,
        final10s_supply_drift_k_min=(last['supply_k']-first_tail['supply_k'])*6,
        final10s_return_drift_k_min=(last['return_k']-first_tail['return_k'])*6,
        final10s_max_return_drift_k_min=(max(last['rack_return_k'])-max(first_tail['rack_return_k']))*6,
        first_sensor_invalid_s=first(lambda f:f['PRE']['measurement']['quality']!='VALID'),
        first_low_flow_fault_s=first(lambda f:'LOW_BRANCH_FLOW_MEASURED' in f['SAFETY']['reason_codes']),
        first_tracking_suspected_s=first(lambda f:f['PRE']['state']=='TRACKING_FAULT_SUSPECTED'),
        first_tracking_confirmed_s=first(lambda f:f['PRE']['state']=='TRACKING_FAULT_CONFIRMED'),
        first_safety_fault_s=fault_since/1e9 if fault_since is not None else None,
        invalid_phase_count=sum(f['PRE']['measurement']['quality']!='VALID' for f in phases),
        return45_acceptance='NOT_REGISTERED_NOT_SCORED',snapshots=snapshots,
        limits=['Numerical/internal physical consistency only, not OEM calibration.',
            'No GPU die or coldplate model. Primary inlet prescribed.',
            'Finite120s horizon, no automatic steady-state/recovery claim.'])
