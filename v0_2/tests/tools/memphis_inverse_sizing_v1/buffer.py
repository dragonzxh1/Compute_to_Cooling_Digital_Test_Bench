"""A and B separately exercised; no mass loss, no free wall heat credit."""
from math import fsum
from .requirements import save,CV
from .audit import need,bound
def run(spec,directory):
    from .group_model.tank import Tank
    cases=[]
    configs=[dict(volume=v,mixing=m,fraction=.7,cold_C=40.9448,short=0.,wall=0.) for v in (12.,15.,18.,20.,24.) for m in (0.,.001,.005)]
    configs += [dict(volume=15.,mixing=0.,fraction=f,cold_C=c,short=0.,wall=0.) for f in (.55,.65,.7,.75,.8,.85,.9,1.) for c in (39.,40.9448,41.2)]
    configs += [dict(volume=15.,mixing=m,fraction=f,cold_C=40.9448,short=0.,wall=0.) for f in (.85,1.) for m in (.001,.005)]
    configs += [dict(volume=15.,mixing=0.,fraction=.7,cold_C=40.9448,short=s,wall=w) for s,w in ((.05,0.),(.2,0.),(0.,2e6))]
    n=spec['layers'];dt=spec.get('dt_s',.1)
    for idx,c in enumerate(configs):
        t=Tank(n,volume=c['volume'],cold_fraction=c['fraction'],cold_k=c['cold_C']+273.15,wall_j_k=c['wall'])
        initial=t.energy();first=t.t[0];external=0.;mx=first;rows=[]
        for k in range(round(90/dt)):
            r=t.advance(dt,330/3600,0.,321.44,314.0948,c['mixing'],c['short'])
            # Independent global external balance, internal mixing cancels.
            external+=dt*CV*(330/3600)*(321.44-r['old_k'][0]);mx=max(mx,t.t[0])
            err=t.energy()-sum(r['old_k'])*t.cap-dt*CV*(330/3600)*(321.44-r['old_k'][0])
            need(abs(err)<=bound(initial,t.energy(),external,ops=8192),'BUFFER_INDEPENDENT_LOCAL_ENERGY')
            rows.append(dict(time_s=(k+1)*dt,outlet_C=t.t[0]-273.15,energy_J=t.energy(),residual_J=err))
        residual=t.energy()-initial-external
        need(abs(residual)<=bound(initial,t.energy(),external,ops=8192*(len(rows)+1)),'BUFFER_INDEPENDENT_GLOBAL_ENERGY')
        a=dict(id=f"{spec['id']}_{idx:02}",tank=spec['tank'],layers=n,dt_s=dt,parameters=c,
            outlet_rise_K=mx-first,max_outlet_C=mx-273.15,volume_m3=c['volume'],initial_cold_nominal_m3=c['volume']*c['fraction'],
            initial_cold_discretized_m3=sum(x<=314.5948 for x in Tank(n,volume=c['volume'],cold_fraction=c['fraction'],cold_k=c['cold_C']+273.15).t)*c['volume']/n,
            usable_sensible_MJ=c['volume']*c['fraction']*CV*(48.29-c['cold_C'])/1e6,
            status='CONDITIONALLY_FEASIBLE' if mx-first<=.5 else 'NO_FEASIBLE_DESIGN_AT_THIS_POINT',
            global_residual_J=residual,actual_flow_m3_h=330.,discharged_m3=8.25,
            wall_model='lumped fluid-isothermal wall' if c['wall'] else 'no wall credit',real_mixing_calibrated=False)
        save(directory/(a['id']+'_steps.json'),rows);cases.append(a)
    save(directory/'buffer_results.json',cases)
    return dict(kind='buffer',cases=cases,numerically_converged='PENDING_CROSS_GRID_COMPARISON',physical_guarantee='NOT_VERIFIED')
