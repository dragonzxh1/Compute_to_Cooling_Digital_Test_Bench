from c2c.core.telemetry import ComputeTelemetry


def total_electrical_power_w(telemetry: ComputeTelemetry, compute: dict) -> float:
    return telemetry.gpu_power_w + float(compute["cpu_power_w"]) + float(compute["other_power_w"])
