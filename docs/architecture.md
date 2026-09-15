# C2C-DTB architecture

C2C-DTB is the simulation and control-development module of a future Liquid Cooling Lifecycle Intelligence Platform. It is not a CFD solver, SCADA/BMS, scheduler, or generic IoT platform.

Core dependency direction:

```text
adapters -> canonical telemetry/state <- physics/control models
                     ^
                     |
          deterministic simulation engine
                     |
             reports and API shells
```

Safety ownership is fixed: L0 physical protection, L1 deterministic PLC, L2 supervisory intent. L2 cannot bypass L1.
