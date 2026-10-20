"""Measurement-only candidate control. No plant, scenario or future schedule API."""
from math import sqrt
from v0_2.tests.tools.m1_engine_v3.common import Record
from v0_2.tests.tools.memphis_control_path_v1.coordination import Controller as SourceController,control_options,ProjectProtection,SourcePLC

class RecoveryController(SourceController):
    def __init__(self,options):
        super().__init__(options=options);self.initial_B=None;self.depletion=False
    def request(self,o,safety,now):
        b=self.contiguous(o.reserve_B_k)
        if self.initial_B is None:self.initial_B=b
        if o.actual_B_load_m3_s>1e-9 and b<self.initial_B-0.5:self.depletion=True
        # Not a schedule injection: a real, released B-flow observation AND TT
        # decline are needed before scheduling recharge. Prior A budget unchanged.
        self.o['disable_B_recharge']=not self.depletion
        r=super().request(o,safety,now)
        r.update(B_depletion_measured=self.depletion,initial_B_TT_estimate_m3=self.initial_B,
            actual_released_A_load_m3_h=o.actual_A_load_m3_s*3600,actual_released_B_load_m3_h=o.actual_B_load_m3_s*3600,
            legacy_load_tank_field_scope='SOURCE_ADAPTER_ONLY; physical CDU primary loops computed separately')
        return r

class CDUController:
    def __init__(self):
        self.state=['NORMAL_A']*3;self.bad=[None]*3;self.entered=[0]*3;self.proof=[None]*3
        self.events=[];self.owner=None;self.primary=[[1.,0.] for _ in range(3)];self.secondary=[[1.,0.] for _ in range(3)]
        self.pumps=[[.9,0.] for _ in range(3)]
    def change(self,i,state,now,reason,obs):
        old=self.state[i]
        if old!=state:self.events.append(dict(unit=i,time_ns=now,from_state=old,to_state=state,reason=reason,measurement_id=obs['id'],sample_ns=obs['sample_ns'],release_ns=obs['release_ns']))
        self.state[i]=state;self.entered[i]=now
    def request(self,obs,now):
        assert obs['sample_ns']<=obs['release_ns']<=now
        fresh=now-obs['sample_ns']<=600000000
        for i,u in enumerate(obs['units']):
            a,b=u['cdu'];state=self.state[i]
            if not fresh:
                if state!='NORMAL_A':self.change(i,'SENSOR_HOLD',now,'STALE_NO_TRUTH_FALLBACK',obs)
                continue
            if state=='NORMAL_A':
                bad=not a['ready'] or a['primary_m3_h']<88 or a['secondary_m3_h']<54.696
                self.bad[i]=now if bad and self.bad[i] is None else self.bad[i] if bad else None
                if self.bad[i] is not None and now-self.bad[i]>=1000000000 and self.owner in (None,i):
                    self.owner=i;self.change(i,'FAULT_DETECTED',now,'RELEASED_CDU_HEALTH_OR_LOCAL_FLOW_NOT_SOURCE_TEMPERATURE',obs)
            elif state=='FAULT_DETECTED':
                self.change(i,'STANDBY_CDU_PERMISSIVE' if b['ready'] else 'NO_STANDBY',now,'PAIR_LOCAL_AVAILABILITY; NO_CROSS_UNIT_BACKUP',obs)
            elif state=='STANDBY_CDU_PERMISSIVE':
                self.primary[i][1]=1.;self.change(i,'STANDBY_CDU_START',now,'OPEN_B_PRIMARY_PAIR; A_B_PRIMARY_FLUIDS_SEPARATE',obs)
            elif state=='STANDBY_CDU_START':
                if b['primary_m3_h']>=109.999999 and b['primary_valve']>=1-1e-9:
                    self.secondary[i][1]=1.;self.pumps[i][1]=.9;self.change(i,'PRIMARY_FLOW_ESTABLISHED',now,'ACTUAL_LOCAL_PRIMARY_FT_AND_VALVES',obs)
                elif now-self.entered[i]>20000000000:self.change(i,'STANDBY_FAILED',now,'PRIMARY_VALVE_OR_FLOW_TIMEOUT_NOT_COMPLETE',obs)
            elif state=='PRIMARY_FLOW_ESTABLISHED':
                if b['secondary_m3_h']>=68.37-1e-7 and b['secondary_valve']>=1-1e-9:
                    self.change(i,'SECONDARY_FLOW_ESTABLISHED',now,'ACTUAL_LOCAL_SECONDARY_FT_NOT_HEADER_TOTAL',obs)
                elif now-self.entered[i]>20000000000:self.change(i,'STANDBY_FAILED',now,'SECONDARY_START_OR_FLOW_TIMEOUT_NOT_COMPLETE',obs)
            elif state=='SECONDARY_FLOW_ESTABLISHED':
                cold=b['primary_inlet_C']+.2<=41.4448 and b['secondary_outlet_C']<=45 and b['hx_W']>0 and max(u['rack_inlet_C'])<=45
                if cold:
                    if self.proof[i] is None:self.proof[i]=now
                    if now-self.proof[i]>=2000000000:self.change(i,'THERMAL_TRANSFER_VERIFIED',now,'ACTUAL_DUTY_AND_FOUR_TEMPERATURES_TWO_FLOWS',obs)
                else:self.proof[i]=None
                if now-self.entered[i]>20000000000:self.change(i,'THERMAL_UNQUALIFIED',now,'FLOW_EXISTS_BUT_COLD_AND_RACK_LIMIT_NOT_MET',obs)
            elif state in ('THERMAL_TRANSFER_VERIFIED','THERMAL_UNQUALIFIED'):
                self.primary[i][0]=self.secondary[i][0]=self.pumps[i][0]=0.
                self.change(i,'ACTIVE_CDU_ISOLATION' if state=='THERMAL_TRANSFER_VERIFIED' else 'UNQUALIFIED_B_SERVICE',now,'CLOSE_FAILED_A_AFTER_ONE_PAIR_CHANGEOVER; NO_LATCH_RESET',obs)
            elif state=='ACTIVE_CDU_ISOLATION':
                if max(a['primary_valve'],a['secondary_valve'])<=1e-9:
                    self.change(i,'CDU_TAKEOVER_COMPLETED',now,'ACTUAL_OLD_PAIR_ISOLATED; CONTINUITY_VERDICT_SEPARATE',obs);self.owner=None
        load_speeds=[]
        for j in range(2):
            n=sum(self.primary[i][j]>.5 or u['cdu'][j]['primary_valve']>1e-9 for i,u in enumerate(obs['units']))
            ratio=n/3
            load_speeds.append(sqrt((135920+20000*ratio**2+38980*ratio**2)/(155920*1.25/.9**2)) if n else 0.)
        return dict(primary=[list(x) for x in self.primary],secondary=[list(x) for x in self.secondary],pumps=[list(x) for x in self.pumps],load_pump_speeds=load_speeds,states=list(self.state),measurement_id=obs['id'],sample_ns=obs['sample_ns'],release_ns=obs['release_ns'],time_ns=now,scope='CANDIDATE_PROJECT_CONTROL_NOT_CUSTOMER_APPROVED_OR_FORMAL_M1')

class CDUPLC:
    """New project-only simulated valve issuer, not certified/frozen PLC proof."""
    def __init__(self):self.prior=None
    def issue(self,request,obs,now):
        assert request['measurement_id']==obs['id'] and obs['sample_ns']<=obs['release_ns']<=now
        assert sum(a[0]>.5 and a[1]>.5 for a in request['secondary'])<=1,'MULTIPLE_PAIR_OVERLAP_DENIED'
        for i in range(3):
            if request['pumps'][i][1]>0:
                assert request['primary'][i][1]==1 and obs['units'][i]['cdu'][1]['primary_m3_h']>=109.999999,'SPARE_SECONDARY_WITHOUT_PRIMARY_FLOW'
        if now-obs['sample_ns']>600000000 and self.prior is not None:
            for key in ('primary','secondary','pumps'):assert request[key]==self.prior[key],'STALE_CDU_CHANGED_ACTUATION'
        self.prior=request
        return Record.make(dict(record_id='PROJECT-CDU-PLC:'+str(now),time_ns=now,measurement_id=obs['id'],request=request,provenance='NEW_PROJECT_SIMULATOR_NOT_CERTIFIED_M1_ISSUE_RECEIPT'))
