from abc import ABC, abstractmethod

from c2c.core.telemetry import ComputeTelemetry


class WorkloadSource(ABC):
    @abstractmethod
    def next_step(self, t_s: float) -> ComputeTelemetry:
        raise NotImplementedError
