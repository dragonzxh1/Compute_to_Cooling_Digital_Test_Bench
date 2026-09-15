from c2c.core.telemetry import ComputeTelemetry
from c2c.workloads.base import WorkloadSource


class SyntheticWorkloadSource(WorkloadSource):
    def __init__(self, workload: dict, compute: dict):
        self.phases = sorted(workload["phases"], key=lambda phase: phase["start_s"])
        self.gpu_count = int(compute["gpu_count"])
        self.idle_w = float(compute["gpu_idle_power_w"])
        self.max_w = float(compute["gpu_max_power_w"])
        self.limit_w = float(compute["gpu_power_limit_w"])

    def next_step(self, t_s: float) -> ComputeTelemetry:
        active = self.phases[0]
        for phase in self.phases:
            if t_s >= phase["start_s"]:
                active = phase
            else:
                break
        util = float(active["utilization_pct"])
        per_gpu_w = min(self.limit_w, self.idle_w + util / 100.0 * (self.max_w - self.idle_w))
        return ComputeTelemetry(
            timestamp_s=t_s,
            gpu_power_w=per_gpu_w * self.gpu_count,
            gpu_util_pct=util,
            sm_activity_pct=util,
            tensor_activity_pct=max(0.0, util - 8.0),
            gpu_power_limit_w=self.limit_w * self.gpu_count,
            workload_type=str(active.get("workload_type", "synthetic")),
        )
