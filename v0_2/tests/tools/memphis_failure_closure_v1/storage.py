"""Component tank discharge/standby and actual post-recharge state checks."""
from math import fsum
from .requirements import save,CV
from .checks import need
def tank_study(spec,directory):
    from .group_model.tank import Tank
    n=spec['layers'];dt=spec.get('dt_s',.1);results=[]
    configs=[dict(volume=v,fraction=f,mixing=m,short=s,cold_C=40.9448,profile='SHARP') for v in (15.,20.) for f in (.7,.85,.9,.95) for m in (0.,.005) for s in (0.,.05)]
    configs += [dict(volume=15.,fraction=.9,mixing=.005,short=0.,cold_C=41.2,profile='SHARP'),dict(volume=15.,fraction=.9,mixing=.005,short=.05,cold_C=40.9448,profile='SMEARED')]
    for i,c in enumerate(configs):
        t=Tank(n,volume=c['volume'],cold_fraction=c['fraction'],cold_k=c['cold_C']+273.15)
        if c['profile']=='SMEARED':
            for _ in range(10):
                old=list(t.t);flux=[0.]*n
                for j in range(n-1):d=.25*(old[j+1]-old[j]);flux[j]+=d;flux[j+1]-=d
                t.t=[a+b for a,b in zip(old,flux)]
        initial=t.energy();start=t.t[0];external=0;mx=start;rows=[]
        for tick in range(round(90/dt)):
            r=t.advance(dt,330/3600,0,321.44,314.0948,c['mixing'],c['short']);external+=dt*CV*330/3600*(321.44-r['old_k'][0]);mx=max(mx,t.t[0])
            need(abs(t.energy()-initial-external)<=1e-9*(abs(initial)+abs(t.energy())+abs(external)),'INDEPENDENT_TANK_CUMULATIVE_ENERGY')
            if (tick+1)%max(1,round(1/dt))==0:rows.append(dict(t_s=(tick+1)*dt,outlet_C=t.t[0]-273.15,energy_J=t.energy()))
        a=dict(id=spec['id']+f'_{i:02}',tank=spec['tank'],layers=n,dt_s=dt,parameters=c,outlet_rise_K=mx-start,max_outlet_C=mx-273.15,
            energy_residual_J=t.energy()-initial-external,status='CONDITIONALLY_FEASIBLE' if mx-start<=.5 else 'NO_FEASIBLE_DESIGN_AT_THIS_POINT',OEM='NOT_VERIFIED')
        save(directory/(a['id']+'_tank_points.json'),rows);results.append(a)
    save(directory/'tank_results.json',results);return dict(kind='tank',cases=results)
def standby(spec,directory):
    from .group_model.tank import Tank
    results=[]
    for label,ua in [('INSULATED_ASSUMPTION',50.),('DEGRADED_ASSUMPTION',500.),('NO_INSULATION_ASSUMPTION',2000.)]:
        t=Tank(80,volume=15,cold_fraction=.9,cold_k=313.65);initial=t.energy();gain=0;points=[]
        for tick in range(7200):
            r=t.advance(1.,0.,0.,321.44,313.65,.001,0)
            heat=ua*(319.15-fsum(t.t)/t.n);t.t=[x+heat/(t.cap*t.n) for x in t.t];gain+=heat
            if tick%60==59:points.append(dict(t_s=tick+1,cold_m3=t.cold_volume(),bottom_C=t.t[0]-273.15,mean_C=fsum(t.t)/80-273.15))
        need(abs(t.energy()-initial-gain)<=1e-8*(initial+t.energy()+abs(gain)),'STANDBY_ENERGY')
        results.append(dict(id=label,UA_W_K=ua,final_cold_m3=t.cold_volume(),gain_MJ=gain/1e6,points=points,OEM='NOT_VERIFIED'))
    return dict(kind='standby',cases=results,scope='15m3 initially90pct40.5C,46C ambient,2h,no withdrawals; realUA unavailable')
