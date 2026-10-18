"""Reuse the existing audited manifold solver; all derived curves remain assumptions."""
from math import fsum,sqrt
from v0_2.hydraulics.graph import HydraulicGraph,HydraulicEdge,PressureNode,EdgeKind
from v0_2.hydraulics.pump import PumpCurve,PumpDrive,pump_energy
from v0_2.hydraulics.solver import solve
from .common import p,REG,RHO,CV,G,check

def edge(name,a,b,k,receiver):
    return HydraulicEdge(name,a,b,EdgeKind.GENERIC_RESISTANCE,p(name+'.K',k,'Pa/(m3/s)^2'),
        (0.,1.),receiver,p(name+'.liquid',1.,'fraction'),p(name+'.basis',1.,'count'))

def drive(efficiency):
    # Document wire-to-liquid budget. VFD/motor split itself is an assumption;
    # every loss enters liquid once, hydraulic work only on passive edges.
    return PumpDrive(p('vfd',.95,'fraction'),p('motor',.9,'fraction'),
        p('pump',efficiency/(.95*.9),'fraction'),p('vfd.liquid',1.,'fraction'),
        p('motor.liquid',1.,'fraction'),p('pump.liquid',1.,'fraction'),
        'return',p('drive.basis',1.,'count'),p('standby',0.,'W'))

def secondary_graph(factors):
    q=68.37/3600;qb=q/6
    nodes=[PressureNode(n,'SECONDARY') for n in ('r','p','hx','sm','rm','filter_return')]
    nodes += [PressureNode('in'+str(i),'SECONDARY') for i in range(6)]
    supply=(edge('HX','p','hx',26600/q**2,'supply'),
        edge('supply_pipe_filter','hx','sm',(61790+25000)/q**2,'supply'))
    branches=tuple((edge('inlet'+str(i),'sm','in'+str(i),171630*f*.1/qb**2,'inlet'+str(i)),
        edge('rack'+str(i),'in'+str(i),'rm',171630*f*.9/qb**2,'rack'+str(i))) for i,f in enumerate(factors))
    ret=(edge('return_filter','rm','filter_return',25000/q**2,'return'),
        edge('return_pipe','filter_return','r',61790/q**2,'return'))
    graph=HydraulicGraph(tuple(nodes),'r','p','sm','rm',supply,branches,ret,'pump')
    k=371810/q**2
    curve=PumpCurve(p('H0',371810*1.25/.9**2,'Pa'),p('pump.K',k*.25,'Pa/(m3/s)^2'),
        (0.,1.),(0.,.05),p('curve.basis',1.,'count'))
    return graph,curve

def primary_load_graph(valve=1.):
    q=330/3600;qb=q/3;k=155920/q**2
    graph=HydraulicGraph(tuple(PressureNode(n,'PRIMARY') for n in ('r','p','sm','rm')),
        'r','p','sm','rm',(edge('supply','p','sm',10000/q**2/max(valve,.001)**2,'primary_supply'),),
        tuple((edge('CDU'+str(i),'sm','rm',135920/qb**2,'primary_return'),) for i in range(3)),
        (edge('return','rm','r',10000/q**2/max(valve,.001)**2,'primary_return'),),'pump')
    curve=PumpCurve(p('load.H0',155920*1.25/.9**2,'Pa'),p('load.K',k*.25,'Pa/(m3/s)^2'),
        (0.,1.),(0.,.2),p('load.curve',1.,'count'))
    return graph,curve

def source_graph(variant,pumps=3,path='WET',valve=1.):
    check(variant in ('V9','PID') and pumps in (1,2,3,4),'SOURCE_VARIANT')
    q=330/3600;modules=5 if path=='WET' else 3
    dp=96520 if path=='WET' else 63210
    common=.2*dp;coil=dp-common
    g=HydraulicGraph(tuple(PressureNode(n,'SOURCE') for n in ('r','p','sm','rm')),
        'r','p','sm','rm',(edge('shared_suction_discharge_headers','p','sm',common/2/q**2/max(valve,.001)**2,'source'),),
        tuple((edge('module'+str(i),'sm','rm',coil/(q/modules)**2,'source'),) for i in range(modules)),
        (edge('shared_return_header','rm','r',common/2/q**2/max(valve,.001)**2,'source'),),'parallel_pumps')
    if variant=='V9':
        hd=RHO*G*34;h0=hd*1.2;kp=(h0-hd)/(115/3600)**2
    else:
        h0=RHO*G*18;kp=(h0-115820)/(110/3600)**2
    curve=PumpCurve(p('source.'+variant+'.H0',h0,'Pa'),
        p('source.parallel.K',kp/pumps**2,'Pa/(m3/s)^2'),(0.,1.),(0.,.25),p('source.assumed',1.,'count'))
    nominal=sqrt((96520+kp/3**2*q**2)/h0)
    return g,curve,nominal

def source_comparison():
    rows=[]
    for variant in ('V9','PID'):
        for pumps in (2,3,4):
            for speed in (.4,.6,.8,1.):
                graph,curve,nominal=source_graph(variant,pumps)
                h=solve(graph,curve,speed,RHO)
                static=REG['source_variants'][variant]['static_gauge_pa']
                pressures=None if static is None else {n:static+v for n,v in h.pressures_pa}
                rows.append(dict(variant=variant,pumps=pumps,speed=speed,flow_m3_h=h.total_flow_m3_s*3600,
                    head_kpa=h.pump_head_pa/1000,shutoff_kpa=curve.shutoff_head_pa.value*speed**2/1000,
                    conditional_gauge_pa=pressures,pressure_reference='PID335890Pa(g), same-elevation assumption' if static is not None else 'V9_STATIC_UNKNOWN_NOT_COMBINED_WITH_PID',
                    curve_basis='SYNTHETIC_QUADRATIC_NOT_OEM',npshr_m=None,npsh_status='NOT_VERIFIED',
                    source_conflict='DESIGN_DECISION_REQUIRED',max_mass_residual_kg_s=h.max_mass_residual_kg_s,
                    hydraulic_energy_residual_w=fsum(d.total_w for d in h.dissipations)-h.pump_head_pa*h.total_flow_m3_s))
    # Required NPSHr cannot be inferred from a Q-H point. Available NPSH is a
    # conditional range only: PG vapour pressure, elevations and suction loss absent.
    available=[(101325+s-v)/(RHO*G) for s in (50000,335890) for v in (2000,12000)]
    return dict(rows=rows,selection=None,npsha_conditional_range_m=[min(available),max(available)],
        npsha_basis='Patm101325, gauge suction50--335.89kPa, Pv2--12kPa; no elevation/velocity/loss proof',
        actual_npshr_m=None,actual_npsh_margin_m=None,equipment_suitability='NOT_VERIFIED',
        wet_coil_run_limit_pa=[100000,600000],secondary_weakest_MAWP_pa=None,
        word34m_with_PID_static_kpa=(335890+RHO*G*34)/1000,
        cross_version_combination='INVALID_AS_A_SELECTED_DESIGN; conditional counterexample only')
