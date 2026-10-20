"""Mixed flow/pressure Fischer-Burmeister solve; original device laws unchanged.

KCL is solved together with each forward-link complementarity condition.
No result clipping, leakage, bypass, pressure-reference tuning or dt change.
"""
import math
import time
import numpy as np
from ..memphis_r12_dynamic_hydraulic_v1.hydraulics import Network as OriginalNetwork


FORWARD=("pump","boundary_pump","check_valve")


def passive_head(q,k,reg):
    """Exact inverse of original smoothed signed sqrt pressure-to-flow law."""
    s=k*q*q; r=math.sqrt(s*s+4*reg*reg)
    a=.5*k*(s+r); root=math.sqrt(a)
    h=q*root
    derivative=root+q*(.5*k*2*k*q*(1+s/r))/(2*root)
    return h,derivative


def mixed_solve(n, edges, anchors, qd, pscale, reg, p0, q0, demand=None):
    """p in scaled pressure; q in qd. Positive demand is prescribed outflow.

    No demand is imposed by the real recirculation model. Nonzero demand is
    used only by the explicitly infeasible mathematical negative control.
    """
    started=time.monotonic();m=len(edges)
    unknown=[i for i in range(n) if i not in anchors]
    incidence=np.zeros((n,m))
    for j,e in enumerate(edges):incidence[e["i"],j]=1;incidence[e["j"],j]=-1
    free=incidence[unknown,:]
    x=np.r_[np.asarray(p0)[unknown],np.asarray(q0)/qd]
    demand=np.zeros(n) if demand is None else np.asarray(demand)/qd
    if abs(float(demand.sum()))>1e-10:
        return None,dict(status="PHYSICAL_INFEASIBLE",reason="Closed network has nonzero net prescribed outflow",
            iterations=0,wall_s=time.monotonic()-started)
    def evaluate(x, jacobian=False):
        p=np.zeros(n);p[unknown]=x[:len(unknown)];y=x[len(unknown):];q=y*qd
        residual=np.r_[free@y+demand[unknown],np.zeros(m)]
        jac=np.zeros((len(residual),len(x))) if jacobian else None
        if jacobian:jac[:len(unknown),len(unknown):]=free
        head_res=[];comp=[];slacks=[]
        for j,e in enumerate(edges):
            forward=e["kind"] in FORWARD
            if forward:h=e["k"]*q[j]*q[j];der=2*e["k"]*q[j]
            else:h,der=passive_head(q[j],e["k"],reg)
            w=(h-e["head"])/pscale-float(incidence[:,j]@p)
            slacks.append(w)
            if forward:
                norm=math.hypot(y[j],w)
                value=norm-y[j]-w
                da=y[j]/norm-1 if norm else 1/math.sqrt(2)-1
                db=w/norm-1 if norm else 1/math.sqrt(2)-1
                comp.append(abs(value))
                head_res.append(abs(w)*pscale if y[j]>1e-8 else max(0.,-w)*pscale)
            else:value=w;da=0.;db=1.;head_res.append(abs(w)*pscale)
            row=len(unknown)+j;residual[row]=value
            if jacobian:
                jac[row,:len(unknown)]=-db*free[:,j]
                jac[row,len(unknown)+j]=da+db*der*qd/pscale
        return residual,jac,p,q,dict(kcl_max=float(np.max(np.abs(incidence@y+demand))),
            pressure_residual_Pa=max(head_res,default=0.),complementarity_residual=max(comp,default=0.),
            min_forward_scaled_flow=min((y[j] for j,e in enumerate(edges) if e["kind"] in FORWARD),default=0.),
            slacks=slacks)
    rank=None;accepted=False
    for iteration in range(100):
        f,jac,p,q,metrics=evaluate(x,True)
        if (max(abs(f),default=0.)<1e-9 and metrics["kcl_max"]<1e-6
            and metrics["pressure_residual_Pa"]<.001
            and metrics["min_forward_scaled_flow"]>=-1e-10):
            accepted=True;break
        step,_,rank,_=np.linalg.lstsq(jac,-f,rcond=1e-12)
        if not np.all(np.isfinite(step)):break
        merit=float(f@f);found=False
        for backtrack in range(24):
            trial=x+step*(.5**backtrack);ft,*_=evaluate(trial)
            if float(ft@ft)<merit*(1-1e-5*.5**backtrack):
                x=trial;found=True;break
        if not found:
            # Bounded merit descent in variable space; final equations unchanged.
            grad=jac.T@f
            for damping in (1e-6,1e-4,1e-2,1.):
                step=np.linalg.lstsq(jac.T@jac+damping*np.eye(len(x)),-grad,rcond=1e-12)[0]
                trial=x+step;ft,*_=evaluate(trial)
                if float(ft@ft)<merit:x=trial;found=True;break
        if not found:break
    f,jac,p,q,metrics=evaluate(x,True)
    metrics.update(status="CONVERGED" if accepted else "NONCONVERGED",iterations=iteration+1,
        rank=int(rank) if rank is not None else None,variables=len(x),
        pressure_nonunique=bool(rank is not None and rank<len(x)),
        physical_violation=bool(metrics["min_forward_scaled_flow"] < -1e-10),
        wall_s=time.monotonic()-started)
    if not accepted:
        return None,dict(metrics,variables_trial=x.tolist(),residual_vector=f.tolist(),
            jacobian=jac.tolist(),pressures_scaled=p.tolist(),flows_trial_m3_s=q.tolist(),edges=edges)
    return (p,q),metrics


class Network(OriginalNetwork):
    def solve(self,valves,speeds,faults):
        active=[]
        for e in self.edges:
            k=e["k"];head=0.
            if e["kind"] in ("motor_valve","isolation_valve"):
                opening=valves.get(e["tag"],0.)
                if opening<1e-6:continue
                k/=opening**2
            if e["kind"]=="pump":
                speed=speeds.get(e["tag"],0.)
                if speed<1e-6:continue
                head=self.a["pump_shutoff_head_Pa"]*speed**2
            if e["kind"]=="boundary_pump":head=self.a["primary_lp_shutoff_Pa"]*self.a["primary_lp_speed"]**2
            if e["kind"]=="filter" and faults.get("filter_block") and "C01B-P2-" in e["tag"]:k*=100
            active.append(dict(e,k=k,head=head))
        n=len(self.names);parent=list(range(n))
        def find(i):
            while parent[i]!=i:i=parent[i]
            return i
        for e in active:parent[find(e["j"])]=find(e["i"])
        zones={}
        for i in range(n):zones.setdefault(find(i),[]).append(i)
        preferred=([self.port_index["G01-NET-A:RET"]] if self.primary else
            [self.port_index[f"G01-C01{s}-P2-XV-RET:OUT"] for s in "AB"])
        anchors=[next((p for p in preferred if p in z),min(z)) for z in zones.values()]
        p0=self.p.copy()
        for z in zones.values():
            anchor=next(i for i in anchors if i in z);p0[z]-=p0[anchor]
        q0=np.array([self.last_flows.get(e["id"],.2*self.qd) for e in active])
        solution,stats=mixed_solve(n,active,anchors,self.qd,self.pscale,
            self.a["pressure_regularization_Pa"],p0,q0)
        if solution is None:
            self.failure=dict(stats,domain_primary=self.primary,nodes=self.names,
                valves=valves,speeds=speeds,faults=faults)
            raise RuntimeError("MCP_HYDRAULIC_NONCONVERGENCE "+str({k:stats[k] for k in ("status","iterations","kcl_max")}))
        p,q=solution
        offset=1000*self.a["primary_reference_kPa_g" if self.primary else "secondary_reference_kPa_g"]
        self.p=p;self.pressures=p*self.pscale+offset
        flows={e["id"]:0. for e in self.edges};flows.update({e["id"]:float(v) for e,v in zip(active,q)})
        self.last_flows=flows;self.last_active=active
        self.last_stats=dict(stats,relative_mass_residual=stats["kcl_max"],newton_iterations=stats["iterations"],zones=len(zones))
        return flows
