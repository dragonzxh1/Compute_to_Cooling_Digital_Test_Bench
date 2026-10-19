"""Independent control-volume equations: NO plant/solver imports."""
from math import fsum,isfinite
CV=1009.*4000.

def verify_cv(du,expected,*terms):
    residual=du-expected
    # Absolute roundoff bound from original operands; not a customer tolerance.
    bound=4096*2**-53*max(1.,fsum(abs(x) for x in terms))
    if not isfinite(residual) or abs(residual)>bound:raise ValueError('INDEPENDENT_CV_ENERGY:'+str((residual,bound)))
    return residual

def independent_rates(t,ql,qs,hot,cold,mixing,short):
    # Face-oriented FV assembly, independently expressed, equal/opposite internal faces.
    n=len(t);vertical=qs-ql
    adv=[vertical*(t[max(0,k-1)] if vertical>=0 else t[min(n-1,k)])*CV for k in range(1,n)]
    result=[]
    for k,x in enumerate(t):
        external=(ql*hot-qs*x)*CV if k==n-1 else ((qs*cold-ql*x)*CV if k==0 else 0.)
        transport=(adv[k-1] if k else 0.)-(adv[k] if k<n-1 else 0.)
        diffusion=CV*mixing*((t[k-1]-x if k else 0.)+(t[k+1]-x if k<n-1 else 0.))
        bypass=CV*short*ql*(t[-1]-t[0])*(1 if k==0 else -1 if k==n-1 else 0)
        result.append(external+transport+diffusion+bypass)
    return result

def verify_layer_rates(r,dt,volume,spec):
    old=r['old_k'];new=r['new_k'];cap=CV*volume/len(old)
    rates=independent_rates(old,r['load_m3_s'],r['source_m3_s'],r['return_k'],r['source_in_k'],spec.get('mixing_m3_s',0.),spec.get('short_circuit',0.))
    for a,b,rate,stored in zip(old,new,rates,r['rates_w']):
        verify_cv(rate,stored,rate,stored,CV*max(old)*(r['load_m3_s']+r['source_m3_s']))
        verify_cv(cap*(b-a),dt*(rate+r['environment_heat_w']/len(old)),cap*a,cap*b,rate*dt)

def assertions():
    from v0_2.tests.tools.memphis_failure_closure_v1.group_model.tank import primary_rates
    from .observer import ObserverPlant
    tests=[]
    for ql,qs in ((.1,0.),(0.,.1),(.1,.1),(.12,.1),(.1,.12)):
        t=[310.,312.,318.,320.];a=independent_rates(t,ql,qs,322.,309.,.001,.01)
        b=primary_rates(t,ql,qs,322.,309.,.001,.01)
        for x,y in zip(a,b):verify_cv(x,y,x,y)
        verify_cv(fsum(a),CV*(ql*(322.-t[0])+qs*(309.-t[-1])),*a)
        tests.append(dict(load_m3_s=ql,source_m3_s=qs,status='EQUAL_OPPOSITE_FACE_MASS_ENERGY_VERIFIED'))
    rejected=0
    for delta in (1.,-1.):
        try:verify_cv(100.,100.+delta,100.,100.)
        except ValueError:rejected+=1
    if rejected!=2:raise ValueError('ENERGY_NEGATIVE_CONTROL_NOT_REJECTED')
    return dict(port_vectors=tests,corrupted_energy_1J_rejected=rejected,
        scope='Discrete equations and accounting verified, not real diffuser calibration')
