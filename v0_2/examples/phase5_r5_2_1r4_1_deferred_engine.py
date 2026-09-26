"""Offline-only R4.1 deferred observable demand and measurement recovery revision."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from v0_2.examples.phase5_r5_2_1r_semantic_engine import ReleasedObservation
from v0_2.examples.phase5_r5_2_1r4_paired_engine import PairedReferenceTrackingQualifier


@dataclass
class DeferredObservableDemand:
    deferred_demand_active: bool
    deferred_demand_id: str
    first_observable_demand_ns: int
    latest_command: float
    resolved_anchor_pair_id: str
    resolved_command_anchor: float
    resolved_measurement_anchor: float
    net_command_demand: float
    expected_direction: int
    measurement_unavailable_since_ns: int
    prior_valid_tracking_state: str
    prior_valid_suspicion_evidence: int
    prior_watch_id: str | None
    source_command_record_id: str
    cancellation_reason: str | None = None
    recovery_reevaluated: bool = False


class DeferredDemandTrackingQualifier(PairedReferenceTrackingQualifier):
    """Preserve observable command demand while measurements are unavailable."""

    def __init__(self, profile: dict, r5_2_classifier: dict):
        super().__init__(profile, r5_2_classifier)
        self.deferred_demand: DeferredObservableDemand | None = None
        self.deferred_events: list[dict] = []
        self.last_valid_state = self.state
        self.measurement_unavailable_since_ns: int | None = None

    def _observable_net(self, item: ReleasedObservation) -> float | None:
        if self.resolved_pair is None:
            return None
        net = item.plc_command - self.resolved_pair.resolved_command_anchor
        if abs(net) < self.material_delta:
            return None
        if self._response_open(item.command_timestamp_ns, abs(net)) is None:
            return None
        return net

    def _process_invalid(self, item: ReleasedObservation) -> None:
        if self.measurement_unavailable_since_ns is None:
            self.measurement_unavailable_since_ns = item.time_ns
        net = self._observable_net(item)
        if net is None:
            if self.deferred_demand is not None and self.deferred_demand.deferred_demand_active:
                if self.deferred_demand.prior_valid_suspicion_evidence == 0 and self.oldest_unresolved_demand_ns is None:
                    self.deferred_demand.deferred_demand_active = False
                    self.deferred_demand.cancellation_reason = "CANCELED_BEFORE_RECOVERY_NO_VALID_FAULT_EVIDENCE"
                    self.deferred_events.append({
                        "time_ns": item.time_ns, "event": "CANCEL", "reason": self.deferred_demand.cancellation_reason,
                        "deferred_demand_id": self.deferred_demand.deferred_demand_id,
                    })
            return
        if self.deferred_demand is None or not self.deferred_demand.deferred_demand_active:
            assert self.resolved_pair is not None
            self.deferred_demand = DeferredObservableDemand(
                True, f"deferred-demand:{len([e for e in self.deferred_events if e['event'] == 'CREATE']) + 1}",
                item.command_timestamp_ns, item.plc_command,
                self.resolved_pair.resolved_anchor_pair_id,
                self.resolved_pair.resolved_command_anchor,
                self.resolved_pair.resolved_measurement_anchor,
                net, 1 if net > 0 else -1,
                self.measurement_unavailable_since_ns,
                self.last_valid_state, self.carried_suspicion_evidence,
                f"motion-watch:{self.watch_number}" if self.oldest_unresolved_demand_ns is not None else None,
                self._command_id(item),
            )
            self.deferred_events.append({
                "time_ns": item.time_ns, "event": "CREATE",
                "deferred_demand": asdict(self.deferred_demand),
            })
        else:
            deferred = self.deferred_demand
            assert deferred is not None
            prior_direction = deferred.expected_direction
            deferred.latest_command = item.plc_command
            deferred.net_command_demand = net
            deferred.expected_direction = 1 if net > 0 else -1
            if deferred.expected_direction != prior_direction:
                self.deferred_events.append({
                    "time_ns": item.time_ns, "event": "REVERSAL",
                    "deferred_demand_id": deferred.deferred_demand_id,
                    "first_observable_demand_ns": deferred.first_observable_demand_ns,
                })
            else:
                self.deferred_events.append({
                    "time_ns": item.time_ns, "event": "UPDATE",
                    "deferred_demand_id": deferred.deferred_demand_id,
                    "first_observable_demand_ns": deferred.first_observable_demand_ns,
                    "net_command_demand": net,
                })

    def _process_recovery(self, item: ReleasedObservation) -> bool:
        deferred = self.deferred_demand
        if deferred is None or not deferred.deferred_demand_active:
            return False
        net = self._observable_net(item)
        if net is None:
            if deferred.prior_valid_suspicion_evidence == 0 and self.oldest_unresolved_demand_ns is None:
                deferred.deferred_demand_active = False
                deferred.cancellation_reason = "CANCELED_AT_RECOVERY_NO_VALID_FAULT_EVIDENCE"
                self.deferred_events.append({
                    "time_ns": item.time_ns, "event": "CANCEL", "reason": deferred.cancellation_reason,
                    "deferred_demand_id": deferred.deferred_demand_id,
                })
            return False
        if self.epoch is None or self.epoch.completion_reason is not None:
            if self.oldest_unresolved_demand_ns is None:
                self.oldest_unresolved_demand_ns = deferred.first_observable_demand_ns
            surrogate = replace(item, command_timestamp_ns=deferred.first_observable_demand_ns)
            self._start_epoch(surrogate, 1 if net > 0 else -1, "DEFERRED_DEMAND_RECOVERY")
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

    def update(self, item: ReleasedObservation) -> dict:
        valid = self._valid(item)
        recovering = valid and self.measurement_unavailable_since_ns is not None
        if not valid:
            self._process_invalid(item)
        reevaluated = self._process_recovery(item) if recovering else False
        prior_pair_id = self.progress_pair.progress_pair_id if self.progress_pair else None
        prior_evidence = self.carried_suspicion_evidence
        record = super().update(item)
        if not valid and self.confirmed_latched:
            # A confirmed fault cannot be cleared by a missing sensor sample.
            record["state"] = "TRACKING_FAULT_CONFIRMED"
            self.state = record["state"]
            if self.transitions and self.transitions[-1]["time_ns"] == item.time_ns:
                self.transitions.pop()
        if valid:
            self.last_valid_state = self.state
            if recovering:
                self.measurement_unavailable_since_ns = None
                if self.deferred_demand is not None and self.deferred_demand.deferred_demand_active:
                    self.deferred_demand.deferred_demand_active = False
                    self.deferred_events.append({
                        "time_ns": item.time_ns, "event": "RECOVERY_CONSUMED",
                        "deferred_demand_id": self.deferred_demand.deferred_demand_id,
                        "qualified_progress": record["qualified_progress"],
                        "fault_evidence_after": self.carried_suspicion_evidence,
                    })
        record["deferred_demand_active"] = bool(
            self.deferred_demand and self.deferred_demand.deferred_demand_active
        )
        record["deferred_demand_id"] = self.deferred_demand.deferred_demand_id if self.deferred_demand else None
        record["first_observable_demand_ns"] = (
            self.deferred_demand.first_observable_demand_ns if self.deferred_demand else None
        )
        record["measurement_unavailable_since_ns"] = self.measurement_unavailable_since_ns
        record["recovery_reevaluated"] = reevaluated
        record["progress_pair_id_before_evaluation"] = prior_pair_id
        record["fault_evidence_before_evaluation"] = prior_evidence
        return record

    def snapshot(self) -> dict:
        result = super().snapshot()
        result["deferred_demand"] = asdict(self.deferred_demand) if self.deferred_demand else None
        result["deferred_events"] = self.deferred_events
        return result
