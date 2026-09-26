"""Offline R4.2 candidate; unresolved evidence and direction have separate lifetimes."""

from dataclasses import asdict, dataclass, replace

from v0_2.examples.phase5_r5_2_1r4_1_deferred_engine import DeferredDemandTrackingQualifier
from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation


@dataclass(frozen=True)
class DirectionalTrackingObligation:
    direction: int
    established_ns: int
    command: float
    resolved_pair_id: str
    progress_pair_id: str | None


class DirectionalObligationTrackingQualifier(DeferredDemandTrackingQualifier):
    def __init__(self, profile: dict, r5_2_classifier: dict):
        super().__init__(profile, r5_2_classifier)
        self.directional_obligation: DirectionalTrackingObligation | None = None
        self.direction_events: list[dict] = []

    def _expected(self, magnitude: float, time_ns: int, start_ns: int) -> float:
        # Preserve watch age, but never demand response before this direction existed.
        if self.directional_obligation is not None:
            start_ns = max(start_ns, self.directional_obligation.established_ns)
        return super()._expected(magnitude, time_ns, start_ns)

    def _record_direction(self, item: ReleasedObservation) -> None:
        net = self._observable_net(item)
        if net is None or self.confirmed_latched:
            return
        direction = 1 if net > 0 else -1
        old = self.directional_obligation
        prior_direction = old.direction if old else self.direction
        if direction == prior_direction:
            return
        assert self.resolved_pair is not None
        self.directional_obligation = DirectionalTrackingObligation(
            direction, item.command_timestamp_ns, item.plc_command,
            self.resolved_pair.resolved_anchor_pair_id,
            self.progress_pair.progress_pair_id if self.progress_pair else None,
        )
        if prior_direction is not None:
            self._close_epoch(item, "OUTAGE_DIRECTION_SUPERSEDED")
        self.direction_events.append({
            "time_ns": item.time_ns, "event": "SUPERSEDE" if prior_direction is not None else "CREATE",
            "prior_direction": prior_direction,
            "obligation": asdict(self.directional_obligation),
            "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
            "carried_suspicion_evidence": self.carried_suspicion_evidence,
        })

    def _process_invalid(self, item: ReleasedObservation) -> None:
        super()._process_invalid(item)
        if (self.deferred_demand is not None and not self.deferred_demand.deferred_demand_active
                and self.oldest_unresolved_demand_ns is None):
            self.directional_obligation = None
        self._record_direction(item)

    def _set_progress_pair(self, item, reason, *, from_resolved=False):
        if reason == "OUTAGE_DIRECTION_RECOVERY" and self.progress_pair is not None:
            # Both values remain paired with their original valid source records.
            return
        super()._set_progress_pair(item, reason, from_resolved=from_resolved)

    def _process_recovery(self, item: ReleasedObservation) -> bool:
        self._record_direction(item)
        deferred = self.deferred_demand
        if deferred is None or not deferred.deferred_demand_active:
            return False
        net = self._observable_net(item)
        if net is None:
            return super()._process_recovery(item)
        if self.epoch is None or self.epoch.completion_reason is not None:
            obligation = self.directional_obligation
            command_ns = obligation.established_ns if obligation else deferred.first_observable_demand_ns
            reason = "OUTAGE_DIRECTION_RECOVERY" if obligation else "DEFERRED_DEMAND_RECOVERY"
            if self.oldest_unresolved_demand_ns is None:
                self.oldest_unresolved_demand_ns = deferred.first_observable_demand_ns
                self.watch_number += 1
                self.watch_events.append({
                    "time_ns": item.time_ns, "event": "START",
                    "watch_id": f"motion-watch:{self.watch_number}",
                    "watch_start_ns": self.oldest_unresolved_demand_ns,
                })
            self._start_epoch(replace(item, command_timestamp_ns=command_ns),
                              1 if net > 0 else -1, reason)
        deferred.recovery_reevaluated = True
        self.deferred_events.append({
            "time_ns": item.time_ns, "event": "RECOVERY_REEVALUATION",
            "deferred_demand_id": deferred.deferred_demand_id,
            "new_command_required": False,
            "first_observable_demand_ns": deferred.first_observable_demand_ns,
            "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
            "measurement_record_id": item.measurement_record_id,
            "progress_pair_id_before_evaluation": self.progress_pair.progress_pair_id if self.progress_pair else None,
        })
        return True

    def _resolve(self, item: ReleasedObservation) -> None:
        super()._resolve(item)
        self.directional_obligation = None

    def update(self, item: ReleasedObservation) -> dict:
        if not isinstance(item, ReleasedObservation):
            raise TypeError("Only released observations may enter the qualifier")
        if self.last_time_ns is not None and item.time_ns <= self.last_time_ns:
            raise ValueError("Strictly increasing causal observations required")
        record = super().update(item)
        record["directional_obligation"] = (
            asdict(self.directional_obligation) if self.directional_obligation else None
        )
        record["epoch_expected_direction"] = self.epoch.expected_direction if self.epoch else None
        return record

    def snapshot(self) -> dict:
        result = super().snapshot()
        result["direction_events"] = self.direction_events
        return result
