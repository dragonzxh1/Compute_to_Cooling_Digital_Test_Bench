from c2c.compute.power import total_electrical_power_w
from c2c.core.telemetry import ComputeTelemetry, HeatLoad


class ComputeToHeatModel:
    def __init__(self, compute: dict, capture: dict):
        self.compute = compute
        self.capture = capture

    def step(self, telemetry: ComputeTelemetry) -> HeatLoad:
        gpu = telemetry.gpu_power_w
        cpu = float(self.compute["cpu_power_w"])
        other = float(self.compute["other_power_w"])
        liquid = (
            float(self.capture["alpha_gpu"]) * gpu
            + float(self.capture["alpha_cpu"]) * cpu
            + float(self.capture["alpha_other"]) * other
        )
        electrical = total_electrical_power_w(telemetry, self.compute)
        return HeatLoad(
            electrical_power_w=electrical,
            liquid_heat_w=liquid,
            air_residual_heat_w=electrical - liquid,
        )
