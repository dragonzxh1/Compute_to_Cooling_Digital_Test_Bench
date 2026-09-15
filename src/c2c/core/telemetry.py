from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ComputeTelemetry(BaseModel):
    timestamp_s: float = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    node_id: str = "node-001"
    rack_id: str = "rack-001"
    gpu_id: str = "aggregate"
    gpu_uuid: str = "SIM-GPU-AGGREGATE"
    gpu_power_w: float = Field(ge=0)
    gpu_util_pct: float = Field(ge=0, le=100)
    sm_activity_pct: float | None = None
    tensor_activity_pct: float | None = None
    gpu_temperature_c: float | None = None
    memory_temperature_c: float | None = None
    gpu_power_limit_w: float | None = None
    gpu_clock_mhz: float | None = None
    workload_id: str = "synthetic-step"
    workload_type: str = "synthetic"


class HeatLoad(BaseModel):
    electrical_power_w: float = Field(ge=0)
    liquid_heat_w: float = Field(ge=0)
    air_residual_heat_w: float = Field(ge=0)


class CDUState(BaseModel):
    timestamp_s: float
    secondary_supply_temp_c: float
    secondary_return_temp_c: float
    secondary_flow_m3h: float = Field(ge=0)
    secondary_supply_pressure_kpa: float
    secondary_return_pressure_kpa: float
    secondary_dp_kpa: float = Field(ge=0)
    primary_supply_temp_c: float
    primary_return_temp_c: float
    primary_flow_m3h: float = Field(ge=0)
    pump_speed_pct: float = Field(ge=0, le=100)
    pump_power_kw: float = Field(ge=0)
    valve_position_pct: float = Field(ge=0, le=100)
    heat_load_kw: float = Field(ge=0)
    heat_rejected_kw: float = Field(ge=0)
    temperature_setpoint_c: float
    status: str = "NORMAL"
    alarms: list[str] = Field(default_factory=list)
