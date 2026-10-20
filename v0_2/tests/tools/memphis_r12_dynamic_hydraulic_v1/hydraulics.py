"""JSON-port network; pipes are zero-volume connections, device losses remain explicit.

No fixed equal rack-flow allocation. Pressure offsets set one reference per
connected pressure zone; not two artificial reservoir grounds in an overlap.
"""
import math
import numpy as np


class Network:
    def __init__(self, graph, domain, assumptions, primary=False):
        self.a=assumptions; self.primary=primary
        self.qd=(110 if primary else 68.37)/3600
        self.pscale=100000.; self.parents={}
        ids={f"G01-C01{s}" for s in "AB"}
        def selected(e):
            return e['fluid_domain']==domain and (any(e['id'].startswith(t+'-') or e['id'].startswith(t+'/') for t in ids)
                or e['id'].startswith('G01-U1-R'))
        edges=[e for e in graph['edges'] if selected(e)]
        def find(p):
            self.parents.setdefault(p,p)
            if self.parents[p]!=p:self.parents[p]=find(self.parents[p])
            return self.parents[p]
        for e in edges:
            find(e['upstream']);find(e['downstream'])
            if e['kind']=='PIPE':self.parents[find(e['downstream'])]=find(e['upstream'])
        self.port_node={p:find(p) for p in list(self.parents)}
        names=sorted(set(self.port_node.values())); self.names=names
        self.index={p:i for i,p in enumerate(names)}
        self.port_index={p:self.index[n] for p,n in self.port_node.items()}
        self.edges=[]; devices={d['tag']:d for d in graph['components']}
        for e in edges:
            if e['kind']=='PIPE':continue
            d=devices[e['equipment_tag']]
            kind=d['kind']; tag=d['tag']
            if kind=='heat_exchanger':
                k=(self.a['primary_hx_drop_at_110_Pa'] if primary else self.a['cdu_hx_drop_at_design_Pa'])/self.qd**2
            elif kind=='rack':k=self.a['rack_drop_at_design_Pa']/(self.qd/6)**2
            elif kind=='filter':k=(self.a['primary_filter_drop_at_110_Pa'] if primary else self.a['secondary_filter_clean_drop_at_design_Pa'])/self.qd**2
            elif kind=='pump':k=self.a['pump_curve_drop_at_design_Pa']/self.qd**2
            elif kind in ('motor_valve','isolation_valve','check_valve'):
                nominal=self.qd/6 if '-R0' in tag else self.qd
                drop=self.a['primary_valve_drop_at_110_Pa'] if primary else self.a['valve_drop_at_design_Pa']
                k=drop/nominal**2
            else:raise ValueError('UNBOUND_DEVICE '+tag)
            self.edges.append(dict(id=e['id'],tag=tag,kind=kind,i=self.port_index[e['upstream']],j=self.port_index[e['downstream']],k=k))
        if primary:
            self.edges.append(dict(id='RESEARCH_BOUNDARY_LP_A',tag='RESEARCH_BOUNDARY_LP_A',kind='boundary_pump',
                i=self.port_index['G01-NET-A:RET'],j=self.port_index['G01-NET-A:SUP'],
                k=self.a['primary_lp_curve_drop_at_330_Pa']/(330/3600)**2))
        self.p=np.zeros(len(names)); self.last_flows={}; self.last_stats={}

    def node(self,port):return self.port_index[port]

    def solve(self, valves, speeds, faults):
        active=[]
        for e in self.edges:
            k=e['k']; head=0.
            if e['kind'] in ('motor_valve','isolation_valve'):
                opening=valves.get(e['tag'],0.)
                if opening<1e-6:continue
                k/=opening**2
            if e['kind']=='pump':
                speed=speeds.get(e['tag'],0.)
                if speed<1e-6:continue
                head=self.a['pump_shutoff_head_Pa']*speed**2
            if e['kind']=='boundary_pump':
                speed=self.a['primary_lp_speed']
                head=self.a['primary_lp_shutoff_Pa']*speed**2
            if e['kind']=='filter' and faults.get('filter_block') and 'C01B-P2-' in e['tag']:k*=100
            active.append(dict(e,k=k,head=head))
        n=len(self.names); groups=list(range(n))
        def find(i):
            while groups[i]!=i:i=groups[i]
            return i
        for e in active:groups[find(e['j'])]=find(e['i'])
        zones={}
        for i in range(n):zones.setdefault(find(i),[]).append(i)
        anchors=[]
        preferred=([self.port_index['G01-NET-A:RET']] if self.primary else
            [self.port_index[f'G01-C01{s}-P2-XV-RET:OUT'] for s in 'AB'])
        for indices in zones.values():anchors.append(next((p for p in preferred if p in indices),min(indices)))
        unknown=[i for i in range(n) if i not in anchors]
        p=self.p.copy(); p-=np.array([p[next(a for a in anchors if find(a)==find(i))] for i in range(n)])
        reg=self.a['pressure_regularization_Pa']
        def evaluate(values,jacobian=False):
            f=np.zeros(n); jac=np.zeros((n,n)) if jacobian else None; flows=[]
            for e in active:
                i,j=e['i'],e['j']; dp=(values[i]-values[j])*self.pscale; h=dp+e['head']; k=e['k']
                if e['kind'] in ('pump','boundary_pump','check_valve'):
                    if h<=0:q=0.;der=0.
                    else:q=math.sqrt(h/k);der=.5/math.sqrt(k*max(h,reg))
                else:
                    den=math.sqrt(k)*(dp*dp+reg*reg)**.25
                    q=dp/den;der=(.5*dp*dp+reg*reg)/(math.sqrt(k)*(dp*dp+reg*reg)**1.25)
                flows.append(q);f[i]+=q/self.qd;f[j]-=q/self.qd
                if jacobian:
                    d=der*self.pscale/self.qd
                    jac[i,i]+=d;jac[i,j]-=d;jac[j,i]-=d;jac[j,j]+=d
            return f,jac,flows
        convergence=False
        for iteration in range(80):
            f,jac,qs=evaluate(p,True);err=float(np.max(np.abs(f)))
            if err<self.a['mass_relative_tolerance']:convergence=True;break
            if not unknown:break
            sub=jac[np.ix_(unknown,unknown)]; rhs=-f[unknown]
            try:delta=np.linalg.solve(sub,rhs)
            except np.linalg.LinAlgError:delta=np.linalg.lstsq(sub,rhs,rcond=1e-12)[0]
            if not np.all(np.isfinite(delta)):raise RuntimeError('NONFINITE_PRESSURE_STEP')
            largest=max(float(np.max(np.abs(delta))),1.);delta/=largest
            merit=float(np.linalg.norm(f));accepted=False
            for backtrack in range(16):
                trial=p.copy();trial[unknown]+=delta*(.5**backtrack)
                ft,_,_=evaluate(trial)
                if float(np.linalg.norm(ft))<merit:
                    p=trial;accepted=True;break
            if not accepted:break
        f,_,qs=evaluate(p)
        err=float(np.max(np.abs(f)))
        if not convergence and err>=self.a['mass_relative_tolerance']:
            raise RuntimeError(f'HYDRAULIC_NONCONVERGENCE domain={self.primary} residual={err} iteration={iteration}')
        # Gauge references are not extra hydraulic sources. Only offsets per zone.
        offset=1000*self.a['primary_reference_kPa_g' if self.primary else 'secondary_reference_kPa_g']
        self.p=p; self.pressures=p*self.pscale+offset
        flows={e['id']:0. for e in self.edges};flows.update({e['id']:q for e,q in zip(active,qs)})
        self.last_flows=flows; self.last_active=active
        self.last_stats=dict(relative_mass_residual=err,newton_iterations=iteration+1,zones=len(zones))
        return flows

    def flow(self,tag):return self.last_flows.get(tag+'/through',0.)
    def hx_flow(self,cdu):return self.last_flows.get(cdu+'-HX/'+('P1' if self.primary else 'P2'),0.)
    def pressure(self,port):return float(self.pressures[self.node(port)])

    def power(self,speeds):
        friction=np.zeros(len(self.names));loss=np.zeros(len(self.names));hydraulic=0.;electric=0.
        for e in self.last_active:
            q=self.last_flows[e['id']];i,j=e['i'],e['j']
            if e['kind'] in ('pump','boundary_pump'):
                hp=max(0.,q*(self.pressures[j]-self.pressures[i]));hydraulic+=hp
                ep=hp/self.a['pump_total_efficiency'] if q>1e-8 else self.a['pump_deadhead_electric_W']
                electric+=ep;loss[j]+=ep-hp
            else:
                heat=q*(self.pressures[i]-self.pressures[j]);friction[j if q>=0 else i]+=max(0.,heat)
        discrepancy=abs(float(np.sum(friction))-hydraulic)
        return dict(electric_W=electric,hydraulic_W=hydraulic,friction_W=float(np.sum(friction)),
            loss_W=float(np.sum(loss)),power_balance_error_W=discrepancy,node_heat_W=friction+loss)
