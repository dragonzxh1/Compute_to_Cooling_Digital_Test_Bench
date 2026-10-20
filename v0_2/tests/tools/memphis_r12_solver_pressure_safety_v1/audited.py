"""Additional exact taps and an explicit research pressure-trip variant."""
import math
from ..memphis_r12_dynamic_hydraulic_v1 import plant as original
from ..memphis_r12_dynamic_hydraulic_v1.control import Controller as OriginalController
from .constrained import Network


class Plant(original.Plant):
    def __init__(self,*args,**kwargs):
        old=original.Network
        try:
            original.Network=Network
            super().__init__(*args,**kwargs)
        finally:original.Network=old

    def physical(self,t):
        p=super().physical(t)
        for side in "AB":
            tag="G01-C01"+side;row=p["cdus"][side]
            for domain,net in (("P1",self.pri),("P2",self.sec)):
                for end in ("IN","OUT"):
                    row[domain+"_"+end+"_kPa_g"]=net.pressure(tag+"-HX:"+domain+"-"+end)/1000
            for name,port in (("pump_in",tag+"-P2-PM1:IN"),("pump_out",tag+"-P2-PM1:OUT"),
                ("filter_in",tag+"-P2-F01:IN"),("filter_out",tag+"-P2-F01:OUT")):
                row[name+"_kPa_g"]=self.sec.pressure(port)/1000
        p["solver"]={key:dict(net.last_stats) for key,net in (("primary",self.pri),("secondary",self.sec))}
        return p


class PressureController(OriginalController):
    """Research fail-stop, not an approved pressure equalization design.

    All triggers use released valid four-port pressure observations. Pump stop
    and primary isolation do NOT guarantee removal of trapped cross-side DP.
    """
    def __init__(self,reg):
        super().__init__(reg);self.pressure_latched=False;self.pressure_events=[]

    def command(self,frame,now,dt):
        if frame is None:return {}
        if frame["sampled_at"]>now or frame["release_at"]>now+1e-9:raise RuntimeError("FUTURE_PRESSURE_FRAME")
        keys=("P1_IN_kPa_g","P2_IN_kPa_g")
        valid=now-frame["sampled_at"]<=self.a["measurement_max_age_s"] and all(
            isinstance(frame["cdus"][s].get(k),(int,float)) and math.isfinite(frame["cdus"][s][k]) for s in "AB" for k in keys)
        dp=max(abs(frame["cdus"][s][keys[0]]-frame["cdus"][s][keys[1]]) for s in "AB") if valid else None
        reason="HX_CROSS_SIDE_DP_OVER_10_KPA" if valid and dp>self.req["hx_inlet_gauge_difference_max_kPa"] else ("INVALID_MEASUREMENT" if not valid else None)
        if reason and not self.pressure_latched:
            self.pressure_latched=True
            self.pressure_events.append(dict(t=now,sampled_at=frame["sampled_at"],release_at=frame["release_at"],
                reason=reason,measured_dp_kPa=dp,policy="RESEARCH_FAIL_STOP_NOT_CERTIFIED_PROTECTION"))
        if self.pressure_latched:
            self.fault_latch=True;self.event(now,"PRESSURE_FAIL_STOP","Stop local pumps; upstream relief/equalization capability not modeled")
            cmd=dict(master=None,speeds={tag:0. for tag in frame["speeds"]},valves={})
            if all(abs(n)<.001 for n in frame["speeds"].values()):
                cmd["valves"]={tag:0. for tag in frame["valves"] if "-P1-" in tag}
            return cmd
        return super().command(frame,now,dt)
