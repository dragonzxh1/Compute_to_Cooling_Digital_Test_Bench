# Second unsealed Memphis execution — retained partial development results

Run38937189134, source6ae4cbf68ad803467c3e526b23af44c821557ae4.
Baseline, six, plant-a and plant-b completed. RECHARGE_SHARED completed900s;
RECHARGE_INDEPENDENT hit the existing PUMP_SPEED_OUT_OF_RANGE guard at1.0116663762.
RECHARGE_INDEP_FAULT and consolidated report did not run. Overall NOT_COMPLETE.

Cause: adapter expressed required nominal speed for330m³/h120kPa as an actual
speed, exceeding the synthetic PID full-speed curve by1.17%. Guard is correct.
Repair: explicit existing physical1.0 VFD saturation, actual deficient flow must
remain an engineering result. No curve/expectation/CPU/memory guard increased.

Review also distinguished state-machine startup readiness from actual cold-water
arrival. Former67.5s latency MUST NOT be cited as cold water restored. New evidence
records actual source return temperature and actual flow to report first arrival.
Raw partial results and all four completed groups are retained, not borrowed as
fresh final delivery PASS. Frozen M1/V1/V2/source snapshots remain unchanged.
