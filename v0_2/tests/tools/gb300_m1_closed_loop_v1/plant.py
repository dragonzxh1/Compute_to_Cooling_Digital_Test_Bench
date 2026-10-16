"""Conservative liquid-only control volumes, using existing HX/pump/network solvers.

No GPU die, cold-plate or actual CDU curve is invented. Each rack owns one
liquid inventory and one offered IT input. The non-liquid fraction exits to air.
"""
from dataclasses import dataclass
from math import fsum, isfinite

from v0_2.cdu.heat_exchanger import Arrangement, HeatExchanger, evaluate
from v0_2.fluids.properties import ConstantCpFluid
from v0_2.hydraulics.graph import EdgeKind, HydraulicEdge, HydraulicGraph, PressureNode
from v0_2.hydraulics.pump import PumpCurve, PumpDrive, pump_energy
from v0_2.hydraulics.solver import solve
from v0_2.thermal.provenance import ParameterRecord


def p(name, value, unit):
    return ParameterRecord(name, value, unit, 'ENGINEERING_ASSUMPTION',
        'gb300_m1_closed_loop_v1/parameter_provenance.json: explicit sensitivity, NOT OEM',
        0., '2026-10-16', (value, value), 'CALIBRATION_REQUIRED')


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


@dataclass(frozen=True)
class PhysicalSnapshot:
    time_ns: int
    supply_k: float
    return_k: float
    rack_return_k: tuple
    flow_m3_s: float
    branch_flows_m3_s: tuple
    dp_pa: float
    actual_speed: float
    actuator_state_id: str
    hydraulic_solution_id: str
    mass_residual_kg_s: float
    pump_curve_residual_pa: float


class SixRackPlant:
    def __init__(self, c):
        self.c = c
        rho, cp = c['density_kg_m3'], c['cp_j_kg_k']
        self.fluid = ConstantCpFluid('sensitivity_PG25_secondary', p('rho', rho, 'kg/m3'),
            p('cp', cp, 'J/(kg*K)'), p('Tref', 300, 'K'), (273.15, 373.15), p('fluid', 1, 'count'))
        primary = ConstantCpFluid('sensitivity_PG25_primary', p('rho.p', rho, 'kg/m3'),
            p('cp.p', cp, 'J/(kg*K)'), p('Tref.p', 300, 'K'), (273.15, 373.15), p('fluid.p', 1, 'count'))
        self.hx = HeatExchanger(p('UA.sensitivity', c['hx_ua_w_k'], 'W/K'), Arrangement.COUNTERFLOW,
            self.fluid, primary, (0, 100), (0, 100), None, p('hx.sensitivity', 1, 'count'))
        # A quadratic sensitivity curve fitted to ONE document design point,
        # NOT a vendor pump curve or an assertion of whole-unit external DP.
        q, dp, n = c['design_secondary_flow_m3_s'], c['design_secondary_dp_pa'], c['design_speed']
        k = dp / q**2
        self.curve = PumpCurve(p('shutoff.sensitivity', dp*c['quadratic_shutoff_factor']/n**2, 'Pa'),
            p('pump.K.sensitivity', dp*(c['quadratic_shutoff_factor']-1)/q**2, 'Pa/(m3/s)^2'),
            (0, 1), (0, q/n), p('pump.sensitivity', 1, 'count'))
        def edge(name, a, b, resistance, receiver):
            return HydraulicEdge(name, a, b, EdgeKind.GENERIC_RESISTANCE,
                p(name+'.K', resistance, 'Pa/(m3/s)^2'), (0, q/n), receiver,
                p(name+'.liquid', 1, 'fraction'), p(name+'.basis', 1, 'count'))
        series = c['series_resistance_fraction']
        self.graph = HydraulicGraph(tuple(PressureNode(x, 'secondary') for x in ('r', 'p', 'sm', 'rm')),
            'r', 'p', 'sm', 'rm', (edge('supply', 'p', 'sm', k*series/2, 'supply'),),
            tuple((edge(r, 'sm', 'rm', k*(1-series)*36, r),) for r in c['rack_ids']),
            (edge('return', 'rm', 'r', k*series/2, 'return'),), 'pump')
        # Existing numerical fixture drive efficiencies and loss destinations.
        self.drive = PumpDrive(p('vfd', .9, 'fraction'), p('motor', .8, 'fraction'),
            p('pump', .75, 'fraction'), p('vfd.liquid', 0, 'fraction'),
            p('motor.liquid', .5, 'fraction'), p('pump.liquid', 1, 'fraction'),
            'return', p('drive.fixture', 1, 'count'), p('standby', 0, 'W'))
        self.temperatures = [c['initial_supply_k'], *([c['initial_return_k']]*7)]
        self.capacities = [rho*cp*v for v in (c['secondary_supply_volume_m3'],
            *([c['rack_fluid_volume_each_m3']]*6), c['secondary_return_volume_m3'])]
        self.initial_energy = self.energy()
        self.totals = dict(it_j=0., liquid_load_j=0., air_load_j=0., pump_electrical_j=0.,
            pump_liquid_j=0., pump_ambient_j=0., hx_to_primary_j=0.)
        self.max_step_residual_j = 0.
        self.max_mass_residual_kg_s = 0.
        self.max_hydraulic_residual_pa = 0.
        self.step_count = 0

    def energy(self):
        return fsum(t*c for t, c in zip(self.temperatures, self.capacities))

    def snapshot(self, now, actual_speed, state_id):
        h = solve(self.graph, self.curve, actual_speed, self.c['density_kg_m3'])
        audit_hydraulics(h, self.c['density_kg_m3'])
        return PhysicalSnapshot(now, self.temperatures[0], self.temperatures[-1],
            tuple(self.temperatures[1:7]), h.total_flow_m3_s, h.branch_flows_m3_s,
            h.pump_head_pa, actual_speed, state_id, 'hydraulic:'+str(now),
            h.max_mass_residual_kg_s, h.pump_curve_residual_pa)

    def advance(self, start_ns, end_ns, speed, loads):
        dt = (end_ns-start_ns)/1e9
        check(dt > 0 and len(loads) == 6 and all(isfinite(x) and x >= 0 for x in loads), 'INVALID_PHYSICS_INPUT')
        c = self.c
        h = solve(self.graph, self.curve, speed, c['density_kg_m3'])
        audit_hydraulics(h, c['density_kg_m3'])
        cv = c['density_kg_m3']*c['cp_j_kg_k']
        flows = [h.total_flow_m3_s, *h.branch_flows_m3_s, h.total_flow_m3_s]
        check(max(dt*cv*f/cap for f, cap in zip(flows, self.capacities)) <= .25,
              'EXPLICIT_ADVECTION_CFL_REDUCE_DT')
        supply, *rest = self.temperatures
        racks, ret = rest[:6], rest[-1]
        hx = evaluate(self.hx, h.total_flow_m3_s*c['density_kg_m3'],
                      c['primary_flow_m3_s']*c['density_kg_m3'], ret, c['primary_inlet_k'])
        pump = pump_energy(self.drive, h.pump_head_pa, h.total_flow_m3_s, dt)
        # Hydraulic dissipation and drive losses each enter liquid exactly once.
        dissipation = {r.edge_id:r.liquid_w for r in h.dissipations}
        liquid = [x*c['liquid_fraction'] for x in loads]
        rates = [cv*h.total_flow_m3_s*(ret-supply)-hx.secondary_out_w+dissipation['supply']]
        rates += [cv*f*(supply-t)+w+dissipation[r] for f,t,w,r in
                  zip(h.branch_flows_m3_s, racks, liquid, c['rack_ids'])]
        rates += [fsum(cv*f*(t-ret) for f,t in zip(h.branch_flows_m3_s, racks))
                  +pump.loss_to_liquid_w+dissipation['return']]
        before = self.energy()
        self.temperatures = [t+dt*w/cap for t,w,cap in zip(self.temperatures, rates, self.capacities)]
        check(all(isfinite(t) and 273.15 <= t <= 373.15 for t in self.temperatures), 'MODEL_TEMPERATURE_RANGE_STOP')
        pump_liquid = pump.loss_to_liquid_w+fsum(dissipation.values())
        residual = self.energy()-before-dt*(fsum(liquid)+pump_liquid-hx.secondary_out_w)
        self.max_step_residual_j = max(self.max_step_residual_j, abs(residual))
        self.step_count += 1
        self.max_mass_residual_kg_s = max(self.max_mass_residual_kg_s, h.max_mass_residual_kg_s)
        self.max_hydraulic_residual_pa = max(self.max_hydraulic_residual_pa, h.pump_curve_residual_pa)
        for key, value in dict(it_j=fsum(loads), liquid_load_j=fsum(liquid), air_load_j=fsum(loads)-fsum(liquid),
            pump_electrical_j=pump.electrical_w, pump_liquid_j=pump_liquid,
            pump_ambient_j=pump.loss_to_ambient_w+fsum(r.ambient_w for r in h.dissipations),
            hx_to_primary_j=hx.secondary_out_w).items():
            self.totals[key] += dt*value
        return dict(start_ns=start_ns, end_ns=end_ns, rack_it_w=list(loads),
            liquid_heat_w=liquid, hx_to_primary_w=hx.secondary_out_w,
            primary_outlet_k=hx.primary_outlet_k, pump_electrical_w=pump.electrical_w,
            energy_residual_j=residual)

    def ledger(self):
        stored = self.energy()-self.initial_energy
        residual = stored-self.totals['liquid_load_j']-self.totals['pump_liquid_j']+self.totals['hx_to_primary_j']
        # Standard gamma_n = n*u/(1-n*u) forward roundoff budget. Count64
        # inventory/ledger rounding operations per interval, not a fitted
        # success tolerance. Numerical convergence is a separate gate.
        unit_roundoff = 2**-53
        operations = 64*(self.step_count+1)
        gamma = operations*unit_roundoff/(1-operations*unit_roundoff)
        bound = gamma*(abs(self.initial_energy)+abs(self.energy())+fsum(self.totals.values()))
        return dict(**self.totals, stored_change_j=stored, fluid_energy_residual_j=residual,
            max_step_residual_j=self.max_step_residual_j, roundoff_bound_j=bound,
            roundoff_operations_budget=operations, roundoff_model='gamma_n=n*u/(1-n*u), u=2^-53',
            max_mass_residual_kg_s=self.max_mass_residual_kg_s,
            max_hydraulic_residual_pa=self.max_hydraulic_residual_pa,
            energy_closed=abs(residual)<=bound,
            heat_source_closed=abs(self.totals['it_j']-self.totals['liquid_load_j']-self.totals['air_load_j'])<=bound,
            pump_energy_closed=abs(self.totals['pump_electrical_j']-self.totals['pump_liquid_j']-self.totals['pump_ambient_j'])<=bound)


def audit_hydraulics(h, density):
    check(all(isfinite(x) and x >= 0 for x in (h.total_flow_m3_s, h.pump_head_pa, *h.branch_flows_m3_s)),
          'NONFINITE_OR_NEGATIVE_HYDRAULICS')
    check(abs(fsum(h.branch_flows_m3_s)-h.total_flow_m3_s)*density <= 1e-9+1e-8*h.total_flow_m3_s*density,
          'INCONSISTENT_HYDRAULIC_STATE')
    check(h.max_mass_residual_kg_s <= 1e-9+1e-8*h.total_flow_m3_s*density, 'MASS_BALANCE_FAIL')
