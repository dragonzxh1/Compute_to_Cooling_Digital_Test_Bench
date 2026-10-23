"""Budget-resolved reduced six-rack network, NOT an OEM calibrated plant.

All edges are explicit. No physical pressure ground is supplied. A numerical
anchor only fixes gauge freedom; gauge pressures must remain None.
The accepted historical mixed solver is imported unchanged.
"""
import math
import numpy as np
from ..memphis_r12_solver_pressure_safety_v1.constrained import mixed_solve


class Network:
    def __init__(self, spec, curve_ratio=1.15):
        self.spec=spec; self.nodes=spec['nodes']; self.edges=spec['edges']
        self.index={s:i for i,s in enumerate(self.nodes)}
        self.qd=68.37/3600; self.pscale=100000.
        self.h0=500000*curve_ratio
        self.pump_k=(self.h0-500000)/(70/3600)**2
        self.p=np.zeros(len(self.nodes));self.q={}

    def solve(self, config):
        active=[]
        for r in self.edges:
            side=r.get('side');kind=r['kind']
            if side and not config['open'][side]:continue
            speed=config['speed'].get(side,0.)
            if kind=='pump' and speed<=0:continue
            qref=r['design_flow_m3_h']/3600
            k=self.pump_k if kind=='pump' else r['design_drop_kPa']*1000/qref**2
            active.append(dict(id=r['id'],kind=kind,i=self.index[r['from']],j=self.index[r['to']],
                k=k,head=self.h0*speed**2 if kind=='pump' else 0.))
        n=len(self.nodes);parent=list(range(n))
        def find(i):
            while parent[i]!=i:i=parent[i]
            return i
        for e in active:parent[find(e['j'])]=find(e['i'])
        zones={}
        for i in range(n):zones.setdefault(find(i),[]).append(i)
        anchors=[min(v) for v in zones.values()]
        p0=self.p.copy()
        for z in zones.values():p0[z]-=p0[min(z)]
        q0=np.array([self.q.get(e['id'],self.qd*.1) for e in active])
        solution,stats=mixed_solve(n,active,anchors,self.qd,self.pscale,.1,p0,q0)
        if solution is None:
            self.failure=stats;raise RuntimeError('UNCHANGED_SOLVER_REJECTED '+str(stats['status']))
        p,q=solution;self.p=p;self.q={e['id']:float(v) for e,v in zip(active,q)}
        incidence=np.zeros((n,len(active)))
        for j,e in enumerate(active):incidence[e['i'],j]=1;incidence[e['j'],j]=-1
        nodal=incidence@q
        friction=0.;hydraulic=0.;records=[]
        for e,v in zip(active,q):
            dp=(p[e['i']]-p[e['j']])*self.pscale
            if e['kind']=='pump':hydraulic-=v*dp
            else:friction+=v*dp
            records.append(dict(e,flow_m3_s=float(v),pressure_drop_Pa=float(dp)))
        # Incidence rank diagnoses gauge freedoms independently of solver's
        # optional warm-start rank. Blocked checks can create EXTRA freedoms.
        rank=int(np.linalg.matrix_rank(incidence))
        shifted=p+7.3
        shift_error=max((abs((shifted[e['i']]-shifted[e['j']])-(p[e['i']]-p[e['j']])) for e in active),default=0.)
        return dict(flow_m3_h={e['id']:float(v*3600) for e,v in zip(active,q)},
            relative_pressure_kPa={s:float(p[i]*100) for i,s in enumerate(self.nodes)},
            physical_gauge_kPa={s:None for s in self.nodes},pressure_status='PRESSURE_UNDERDETERMINED',
            numerical_anchors=[self.nodes[i] for i in anchors],physical_pressure_references=0,
            connected_zones=len(zones),incidence_rank=rank,incidence_gauge_nullity=n-rank,
            gauge_shift_edge_error_scaled=shift_error,
            solver=stats,node_mass_residual_m3_s=nodal.tolist(),
            hydraulic_W=float(hydraulic),friction_W=float(friction),
            power_error_W=float(friction-hydraulic),edges=records,
            note='Relative head loss only; stopped-pump trapped pressure, compliance, waterhammer and NPSH not modeled')


def design_speed(ratio=1.15):
    h0=500000*ratio;k=(h0-500000)/(70/3600)**2
    return math.sqrt((371810+k*(68.37/3600)**2)/h0)
