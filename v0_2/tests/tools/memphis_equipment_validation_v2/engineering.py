"""Equipment requirements, explicit evidence classes and bounded comparisons."""
from math import log,sqrt
from .audit import need

def required_ua(q_kw,primary_c,secondary_c,primary_m3_h=110,secondary_m3_h=68.37):
    cp=1009*4000/3600000
    po=primary_c+q_kw/(cp*primary_m3_h);si=secondary_c+q_kw/(cp*secondary_m3_h)
    a=si-po;b=secondary_c-primary_c
    need(a>0 and b>0,'INFEASIBLE_HX_ENDPOINTS')
    lm=b if abs(a-b)<1e-12 else (a-b)/log(a/b)
    return dict(q_kw=q_kw,primary_in_c=primary_c,primary_out_c=po,secondary_out_c=secondary_c,secondary_in_c=si,
        primary_m3_h=primary_m3_h,secondary_m3_h=secondary_m3_h,LMTD_K=lm,required_UA_kW_K=q_kw/lm,
        provenance='DERIVED_REQUIREMENT',basis='constant PG25 design properties, ideal counterflow, no fouling/manufacturing margin')

def equipment():
    points=[required_ua(888.12,37,40,secondary_m3_h=49.19),required_ua(894.36,41,44),required_ua(1100,41,44)]
    fields=['Rated capacity','Exact project capacity','Primary flow and DeltaP','Secondary flow and DeltaP','External available head','PG25 compatibility','Fouling allowance','MAWP','Redundant pumps','Control interface','Fault recovery','Installation maintenance']
    candidates=[]
    def candidate(name,values,status,source,note):
        candidates.append(dict(name=name,parameters={f:values.get(f,dict(value=None,provenance='UNKNOWN')) for f in fields},selection=status,source=source,note=note,procurement='NOT_RELEASED'))
    def datum(v,kind):return dict(value=v,provenance=kind)
    candidate('Custom CDU1100',{'Rated capacity':datum('1100kW requirement, not verified rating','CUSTOMER_DESIGN'),
        'Primary flow and DeltaP':datum('110m3/h; complete path budget155.92kPa includes quoted PHE74.714kPa','CUSTOMER_DESIGN'),
        'Secondary flow and DeltaP':datum('49.19--68.37m3/h; hot371.81kPa complete path','CUSTOMER_DESIGN'),
        'External available head':datum('Required external295.21kPa hot /152.81kPa normal from project budget, NOT supplier available head','DERIVED_REQUIREMENT'),
        'Redundant pumps':datum('2x100% per CDU; paired CDU1+1 per six racks','CUSTOMER_DESIGN')},'CONDITIONALLY_SUITABLE','00/01 hash-bound final sources','Require project thermal guarantee, external head, recovery and pressure proof; no final equipment PASS')
    candidate('Alfa Laval plate HX option',{},'NOT_VERIFIED','https://www.alfalaval.com/en-us/industries/hvac/data-center-cooling/','Component manufacturer/application evidence only; no exact selected model. Cannot inherit Sanhua DeltaP/MAWP')
    candidate('Sanhua S200AL-246H plate HX',{'Primary flow and DeltaP':datum('74.714kPa@110m3/h quoted by customer document','CUSTOMER_DESIGN'),
        'Secondary flow and DeltaP':datum('26.626kPa@68.4m3/h quoted by customer document','CUSTOMER_DESIGN'),
        'MAWP':datum('3MPa both sides quoted in process08; original OEM sheet absent','ENGINEERING_ASSUMPTION')},'NOT_VERIFIED','00 model and embedded figures; prior Sanhua reaudit hashed inputs','Exact project UA, fouling and original manufacturer selection sheet missing; not an entire CDU model')
    candidate('Vertiv XDU1350',{'Rated capacity':datum('1368kW at4K ATD, catalog condition','OEM_CONFIRMED'),
        'Redundant pumps':datum('N+1 and three-pump N modes distinguished in SL70618','OEM_CONFIRMED'),
        'Secondary flow and DeltaP':datum('Guide thermal graph water1200L/min; not project PG25 guarantee','OEM_CONFIRMED'),
        'External available head':datum('Catalog dual-pump1200L/min at244kPa external; different project flow/fluid, full curve required','OEM_CONFIRMED'),
        'Control interface':datum('Modbus register appendix in SL70618','OEM_CONFIRMED')},'NOT_VERIFIED','https://www.vertiv.com/48ef40/globalassets/products/thermal-management/high-density-solutions/liebert-xdu1350-coolant-distribution-unit-application-and-planning-guide-sl-70618.pdf','3K/PG25/external head/pump mode must be quoted; 1368kW alone cannot establish project suitability')
    candidate('Motivair MCDU40 / MCDU50 inquiry',{'Rated capacity':datum('Catalog MCDU40 1250kW and MCDU50 1725kW at90F primary,113/149F secondary; different condition from project','OEM_CONFIRMED'),
        'Primary flow and DeltaP':datum('Nominal primary420USgpm; DeltaP not obtained','OEM_CONFIRMED'),
        'Secondary flow and DeltaP':datum('MCDU40 nominal240USgpm; MCDU50 340USgpm; full curve required','OEM_CONFIRMED'),
        'External available head':datum('Catalog nominal32/30psi respectively, at their catalog flow; not project proof','OEM_CONFIRMED'),
        'Redundant pumps':datum('Catalog dual variable-speed pumps; precise single-pump ability required','OEM_CONFIRMED'),
        'Control interface':datum('Modbus/BACnet options in brochure','OEM_CONFIRMED')},'NOT_VERIFIED','https://www.motivaircorp.com/uploads/files/brochures/CDU_Brochure_2023.pdf','Catalog fluid labels mention25%PG but capacity footnote says100%water: seek written clarification. Do not treat as confirmed PG25 project rating or current orderable BOM')
    rfi=[dict(id='RFI-'+str(i+1).zfill(2),topic=x,blocking=True) for i,x in enumerate([
        'GB300 ordered model: actual liquid fraction, max return temperature, min/max per-rack flow and Q-DeltaP, weakest MAWP',
        'CDU supplier/BOM versus plate HX manufacturer: exact37/40 and41/44 points and1100kW guarantee with four temperatures, flow, fouling, tolerances and PG25 formula',
        'Pump full PG25 Q-H-eta-power-NPSHr curves at all VFD speeds; simultaneous standby/start behavior; shutoff and pressure limits',
        'Design authority adjudication:00/01 34m shared-source arrangement versus R10 <=18m/independent recharge; no software approval',
        'Tower exact BKC11.3*2.3/GESC-K70B23DE DB/WB performance maps, dry rated inlet, water/PG correction, fans, spray and makeup',
        '15m3 tank distributors, real effective volume and outlet profile at330m3/h90s, mixing/short circuit; valve stroke/Kv and pump startup',
        'Static pressure, elevations, PG vapour pressure, suction losses, relief, expansion, weakest component and transient study',
        'Actual CAPEX, service/isolation access, operating efficiency, water quality, tariff and lifecycle assumptions'])]
    options=[dict(option=name,decision=decision,scope=scope) for name,decision,scope in [
        ('00/01 current plus shared segmented recharge','DESIGN_INFORMATION_INSUFFICIENT','Current final topology; thermal and restoration results separately evaluated'),
        ('R10 independent recharge','DESIGN_INFORMATION_INSUFFICIENT','Alternative: needs added pump/pipe/power, OEM curve,330m3/h proof and design approval'),
        ('Shared standby CDU across three units','DESIGN_INFORMATION_INSUFFICIENT','Not implemented customer topology; needs cross-tie manifold/valves, extra loss, failure-domain and maintenance review; no assumed reliability/cost advantage'),
        ('Hybrid dry/wet packaged source','DESIGN_INFORMATION_INSUFFICIENT','Conditional total reject2716.15kW; no actual common-condition map or cost'),
        ('Earlier measured reserve transfer','MODIFICATION_RECOMMENDED','Study new registered trigger/delay only after diagnosing existing trace; current44.5 trigger retained this run')]]
    return dict(points=points,external_head_requirement_kpa=dict(hot=295.21,normal=152.81,provenance='DERIVED_REQUIREMENT',basis='complete secondary path minus CDU internal HX/filter losses; never compare catalog external head directly with371.81'),UA_study=[dict(UA_kW_K=v,operating_margin_kW_K=v-points[1]['required_UA_kW_K'],guarantee_margin_kW_K=v-points[2]['required_UA_kW_K'],provenance='ENGINEERING_ASSUMPTION',OEM_available_UA=None) for v in (110,183.30,209.28,220)],
        candidates=candidates,RFI=rfi,options=options,prices=None,CAPEX_OPEX='NOT_VERIFIED_NO_SUPPLIER_PRICE_OR_ANNUAL_CALIBRATED_MAP',
        cost_formula='CAPEX=sum(actual quotes)+installation+spares; OPEX=integral(actual pump/fan kW)*tariff + water_m3*water_sewer_tariff + maintenance; tariffs/annual hours UNKNOWN')

def curves():
    rows=[];rho=1009;g=9.80665;q=330/3600
    for variant in ('V9_34m','R10_18m'):
        hd=rho*g*34;h0=1.2*hd if variant=='V9_34m' else rho*g*18
        kp=(h0-hd)/(115/3600)**2 if variant=='V9_34m' else (h0-115820)/(110/3600)**2
        for pumps in (2,3,4):
            for speed in (.3,.4,.6,.8,1.):
                actual=sqrt(h0*speed**2/(96520/q**2+kp/pumps**2));head=96520*(actual/q)**2
                for eta in (.6,.7,.8):
                    rows.append(dict(variant=variant,pumps=pumps,speed=speed,per_pump_m3_h=actual*3600/pumps,total_m3_h=actual*3600,head_kpa=head/1000,shutoff_kpa=h0*speed**2/1000,efficiency=eta,electrical_kw=actual*head/eta/1000,
                        conditional_suction_gauge_kpa=50,conditional_min_abs_kpa=151.325,conditional_max_abs_kpa=151.325+head/1000,
                        NPSHa_conditional_range_m=[(101325+50000-pv)/(rho*g) for pv in (12000,2000)],NPSHr_m=None,minimum_MAWP_pa=None,
                        provenance='ENGINEERING_ASSUMPTION',operating_point_status='SYNTHETIC_NOT_OEM',transient_pressure='NOT_VERIFIED'))
    return dict(rows=rows,wet_run_kpa=96.52,selection_envelope_kpa=115.82,load_loop_separate_kpa=155.92,
        conflict='DESIGN_SIGNATURE_REQUIRED;00/01 current retained;R10 comparison only',procurement='BLOCKED_PENDING_FULL_CURVES_STATIC_REFERENCE_AND_WEAK_MAWP',
        bounds='steady same-elevation liquid circuit only; suction pressure50kPa is a conditional minimum design assumption, no water-hammer or real NPSH margin proof')
