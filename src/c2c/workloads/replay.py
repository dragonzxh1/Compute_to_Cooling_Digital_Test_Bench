from pathlib import Path

import pandas as pd

from c2c.core.telemetry import ComputeTelemetry
from c2c.workloads.base import WorkloadSource


class TraceReplaySource(WorkloadSource):
    """CSV replay boundary reserved for later data-driven scenarios."""

    def __init__(self, path: str | Path):
        self.frame = pd.read_csv(path).sort_values("timestamp_s")

    def next_step(self, t_s: float) -> ComputeTelemetry:
        row = self.frame.iloc[(self.frame["timestamp_s"] - t_s).abs().argmin()]
        return ComputeTelemetry(**row.to_dict())
