"""Closed recirculating pipe sizing with heat gain and pump heat, physical lower-bound plant."""
from math import fsum,log
from .requirements import CV,save
from .audit import need,bound
def run(spec,directory):
    from .group_model.tank import TransportPipe
    cases=[]
    for flow in (5.,10.,20.,60.,90.):
      for power in (25.,100.,750.):
       for ambient_ua in (0.,.5):
        pipe=TransportPipe(volume=2.75);initial=pipe.energy();q=flow/3600;dt=1.;ambient=46+273.15;floor=314.0948
        pump=q*20000/.65 # registered20kPa loop, not an OEM pump
        removed=gained=0.;ready=None;rows=[];peak=0.
        for tick in range(3600):
            old=pipe.energy();hot=pipe.t[-1]+pump/(CV*q)
            reject=min(power*1000,CV*q*max(0.,hot-floor));inlet=hot-reject/(CV*q)
            outlet=pipe.advance(dt,q,inlet)
            heat=ambient_ua*1000*(ambient-fsum(pipe.t)/pipe.n)
            pipe.t=[t+heat*dt/(pipe.cap*pipe.n) for t in pipe.t]
            err=pipe.energy()-old-dt*(pump-reject+heat)
            need(abs(err)<=bound(old,pipe.energy(),pump,reject,heat),'PRECOOL_ENERGY_OWNERSHIP')
            removed+=reject*dt;gained+=heat*dt;peak=max(peak,reject)
            if ready is None and max(pipe.t)<=314.5948:ready=tick+1
            rows.append(dict(time_s=tick+1,far_end_C=pipe.t[-1]-273.15,hottest_pipe_C=max(pipe.t)-273.15,removed_kW=reject/1000,ambient_gain_kW=heat/1000,pump_kW=pump/1000,residual_J=err))
        err=pipe.energy()-initial-3600*pump+removed-gained
        need(abs(err)<=bound(initial,pipe.energy(),removed,gained,pump*3600,ops=8192*3600),'PRECOOL_GLOBAL_ENERGY')
        ua=ambient_ua*1000
        hold=None if ua==0 else CV*2.75/ua*log((46-40.9448)/(46-41.4448))
        a=dict(id=f"P{len(cases):02}",flow_m3_h=flow,cooling_capacity_kW=power,ambient_UA_kW_K=ambient_ua,
            ready_seconds=ready,ready_definition='all physical pipe cells<=41.4448C; ideal lower-bound plant, not installed sensor proof',
            status='CONDITIONALLY_FEASIBLE' if ready is not None else 'NO_FEASIBLE_DESIGN_AT_THIS_POINT',
            final_hottest_C=max(pipe.t)-273.15,removed_MJ=removed/1e6,mean_thermal_cooling_kW=removed/3600/1000,
            minimum_hold_thermal_kW=ambient_ua*(46-40.9448)+pump/1000,
            compressor_or_fan_electric_kW=None,registered_pump_kW=pump/1000,physical_global_residual_J=err,
            well_mixed_outage_hold_seconds=hold,outage_note='optimistic isothermal insulated-pipe model; ifUA0 hold is unbounded only in ideal model; actualUA/ambient/water hammer unknown')
        save(directory/(a['id']+'_steps.json'),rows);cases.append(a)
    save(directory/'precool_results.json',cases)
    return dict(kind='precool',cases=cases,OEM_GUARANTEED_VALUE=None,flow_pressure_basis='20kPa,eta0.65 hypothetical preconditioning loop; COP and fan map unavailable')
