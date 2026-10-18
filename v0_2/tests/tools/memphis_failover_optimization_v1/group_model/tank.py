"""Conservative extension of dynamic_v4 primaryRates, with complete15m3 inventory.

Bottom index0/top indexN-1. 70% is INITIAL cold inventory, never a removal of
30% from heat capacity. Mixing and internal short circuit are explicit assumptions.
"""
from math import fsum,isfinite
from .common import CV,check,rounding_bound

def primary_rates(t,load,source,return_hot,source_cold,mixing=0.,short=0.):
    net=source-load;n=len(t);r=[0.]*n
    r[-1]+=CV*(load*return_hot-source*t[-1])
    r[0]+=CV*(source*source_cold-load*t[0])
    for i in range(n-1):
        flux=CV*net*(t[i] if net>=0 else t[i+1]);r[i]-=flux;r[i+1]+=flux
        mixing_flux=CV*mixing*(t[i+1]-t[i]);r[i]+=mixing_flux;r[i+1]-=mixing_flux
    # Explicit top-bottom internal recirculation, not a fictional external loss.
    flux=CV*short*load*(t[-1]-t[0]);r[0]+=flux;r[-1]-=flux
    return r

class Tank:
    def __init__(self,layers=20,kind='STRATIFIED',warm=False):
        self.n=1 if kind=='MIXED' else layers;self.volume=15.;self.cap=CV*self.volume/self.n
        if warm:self.t=[321.44]*self.n
        elif self.n==1:self.t=[.7*314.0948+.3*321.44]
        else:self.t=[314.0948 if i<round(.7*self.n) else 321.44 for i in range(self.n)]
        self.initial_energy=self.energy();self.external_j=0.;self.max_residual_j=0.

    def energy(self):return self.cap*fsum(self.t)

    def measured_layers(self):
        # Four explicit virtual thermometers, not hidden access to all layers.
        return tuple(self.t[round(f*(self.n-1))] for f in (0.,1/3,2/3,1.))

    def cold_volume(self,threshold_k=314.5948):
        return sum(x<=threshold_k for x in self.t)*self.volume/self.n

    def advance(self,dt,load,source,return_hot,source_cold,mixing=0.,short=0.,pump_loss_w=0.):
        old=list(self.t);before=self.energy()
        rates=primary_rates(old,load,source,return_hot,source_cold,mixing,short)
        rates[-1]+=pump_loss_w
        check(dt*(load+source+2*mixing+short*load)/(self.volume/self.n)<=.5,'TANK_CFL_REDUCE_DT')
        self.t=[x+dt*r/self.cap for x,r in zip(old,rates)]
        check(all(isfinite(t) and 273.15<=t<=373.15 for t in self.t),'TANK_MODEL_RANGE_STOP')
        expected=dt*(CV*(load*(return_hot-old[0])+source*(source_cold-old[-1]))+pump_loss_w)
        residual=self.energy()-before-expected
        check(abs(residual)<=rounding_bound(before,self.energy(),expected,operations=512),'TANK_CONSERVATION')
        self.external_j+=expected;self.max_residual_j=max(self.max_residual_j,abs(residual))
        return dict(old_k=old,new_k=list(self.t),rates_w=rates,load_m3_s=load,source_m3_s=source,
            return_k=return_hot,source_in_k=source_cold,pump_loss_w=pump_loss_w,residual_j=residual)

class TransportPipe:
    def __init__(self,cold=False,volume=2.75):
        self.volume=volume;self.n=10;self.cap=CV*self.volume/self.n
        self.t=[314.0948 if cold else 321.44]*self.n
        self.initial_energy=self.energy();self.max_residual_j=0.
    def energy(self):return self.cap*fsum(self.t)
    def advance(self,dt,flow,inlet):
        old=list(self.t);out=old[-1]
        check(dt*flow/(self.volume/self.n)<=.5,'SOURCE_PIPE_CFL')
        self.t=[x+dt*CV*flow*(a-x)/self.cap for a,x in zip([inlet,*old[:-1]],old)]
        residual=self.energy()-self.cap*fsum(old)-dt*CV*flow*(inlet-out)
        check(abs(residual)<=rounding_bound(self.cap*fsum(old),self.energy(),dt*CV*flow*(inlet-out),operations=512),'PIPE_CONSERVATION')
        self.max_residual_j=max(self.max_residual_j,abs(residual))
        return out

def verify_upstream_vectors(data):
    maximum=0.
    for v in data['vectors']:
        actual=primary_rates(v['temps'],v['load'],v['source'],v['returnHot'],v['sourceCold'],v['mixing'])
        for a,b in zip(actual,v['rates']):
            check(abs(a-b)<=rounding_bound(a,b,operations=512),'EXISTING_PROJECT_TANK_PORT_DRIFT')
            maximum=max(maximum,abs(a-b))
    return dict(vectors=len(data['vectors']),max_rate_difference_w=maximum,
        scope='PORT_EQUIVALENCE_AND_CONSERVATION_NOT_REAL_TANK_CALIBRATION')
