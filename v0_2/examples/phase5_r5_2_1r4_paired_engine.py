"""Offline R4 paired-reference tracking candidate; never imported by production Safety."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from v0_2.examples.phase5_r5_2_1r_semantic_engine import (
    OfflineTrackingQualifier,
    ReleasedObservation,
)


@dataclass(frozen=True)
class ResolvedTrackingAnchorPair:
    resolved_command_anchor: float
    resolved_measurement_anchor: float
    resolved_anchor_pair_id: str
    resolved_anchor_ns: int
    source_obligation_id: str | None
    source_epoch_id: str | None
    establishment_reason: str


@dataclass(frozen=True)
class ProgressCheckpointPair:
    progress_command_reference: float
    progress_measurement_reference: float
    progress_pair_id: str
    progress_pair_ns: int
    source_epoch_id: str
    source_measurement_record_id: str
    source_command_record_id: str
    update_reason: str


class PairedReferenceTrackingQualifier(OfflineTrackingQualifier):
    """Causal candidate using frozen numeric profile and two atomic reference pairs."""

    def __init__(self, profile: dict, r5_2_classifier: dict):
        super().__init__(profile, r5_2_classifier)
        self.resolved_pair: ResolvedTrackingAnchorPair | None = None
        self.progress_pair: ProgressCheckpointPair | None = None
        self.resolved_pair_events: list[dict] = []
        self.progress_pair_events: list[dict] = []
        self.oldest_unresolved_demand_ns: int | None = None
        self.latest_demand: float = 0.0
        self.direction: int | None = None
        self.qualified_progress_seen = False
        self.suspected_since_ns: int | None = None
        self.confirmed_since_ns: int | None = None
        self.carried_suspicion_evidence = 0
        self.credited_motion = 0.0

    @staticmethod
    def _command_id(item: ReleasedObservation) -> str:
        return str(getattr(item, "plc_command_id", f"released-command:{item.command_timestamp_ns}"))

    def _set_resolved_pair(self, item: ReleasedObservation, reason: str) -> None:
        assert self._valid(item) and item.measured_speed is not None
        previous = self.resolved_pair
        pair = ResolvedTrackingAnchorPair(
            item.plc_command, item.measured_speed,
            f"resolved-pair:{len(self.resolved_pair_events) + 1}", item.time_ns,
            self.epoch.tracking_epoch_id if self.epoch else None,
            self.epoch.tracking_epoch_id if self.epoch else None, reason,
        )
        self.resolved_pair = pair
        self.resolved_pair_events.append({
            "time_ns": item.time_ns, "previous": asdict(previous) if previous else None,
            "new": asdict(pair), "reason": reason,
        })

    def _set_progress_pair(self, item: ReleasedObservation, reason: str, *, from_resolved: bool = False) -> None:
        assert self._valid(item) and item.measured_speed is not None and self.epoch is not None
        previous = self.progress_pair
        if from_resolved:
            assert self.resolved_pair is not None
            command = self.resolved_pair.resolved_command_anchor
            measurement = self.resolved_pair.resolved_measurement_anchor
            pair_ns = self.resolved_pair.resolved_anchor_ns
            measurement_id = f"resolved:{self.resolved_pair.resolved_anchor_pair_id}"
            command_id = measurement_id
        else:
            command = item.plc_command
            measurement = item.measured_speed
            pair_ns = item.time_ns
            measurement_id = item.measurement_record_id
            command_id = self._command_id(item)
        pair = ProgressCheckpointPair(
            command, measurement, f"progress-pair:{len(self.progress_pair_events) + 1}",
            pair_ns, self.epoch.tracking_epoch_id, measurement_id, command_id, reason,
        )
        self.progress_pair = pair
        self.progress_pair_events.append({
            "time_ns": item.time_ns, "previous": asdict(previous) if previous else None,
            "new": asdict(pair), "reason": reason,
            "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
        })

    def _start_epoch(self, item: ReleasedObservation, direction: int, reason: str) -> None:
        assert self._valid(item) and item.measured_speed is not None
        self.epoch_number += 1
        epoch_id = f"tracking-epoch:{self.epoch_number}"
        if self.oldest_unresolved_demand_ns is None:
            self.oldest_unresolved_demand_ns = item.command_timestamp_ns
            self.watch_number += 1
            self.watch_events.append({
                "time_ns": item.time_ns, "event": "START",
                "watch_id": f"motion-watch:{self.watch_number}",
                "watch_start_ns": self.oldest_unresolved_demand_ns,
            })
        self.direction = direction
        self.qualified_progress_seen = False
        self.latest_demand = abs(item.plc_command - (
            self.resolved_pair.resolved_command_anchor if self.resolved_pair else item.measured_speed
        ))
        from v0_2.examples.phase5_r5_2_1r_semantic_engine import TrackingEpoch

        self.epoch = TrackingEpoch(
            epoch_id, item.command_timestamp_ns,
            self.resolved_pair.resolved_command_anchor if self.resolved_pair else item.measured_speed,
            item.plc_command,
            self.resolved_pair.resolved_measurement_anchor if self.resolved_pair else item.measured_speed,
            direction, self.oldest_unresolved_demand_ns,
            self._response_open(item.command_timestamp_ns, self.latest_demand) or item.time_ns,
            "HANDOFF_PENDING", measurement_record_id=item.measurement_record_id,
        )
        self.epoch_events.append({
            "time_ns": item.time_ns, "event": "START", "reason": reason,
            "epoch_id": epoch_id, "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
            "expected_direction": direction,
        })
        self._set_progress_pair(item, reason, from_resolved=reason != "MATERIAL_REVERSAL" and self.resolved_pair is not None)

    def _resolve(self, item: ReleasedObservation) -> None:
        assert self.epoch is not None
        self.epoch.qualified_progress_seen = True
        self._close_epoch(item, "STEADY_WITHIN_TRACKING_TOLERANCE")
        self.watch_events.append({
            "time_ns": item.time_ns, "event": "RESOLVE",
            "watch_id": f"motion-watch:{self.watch_number}",
            "reason": "QUALIFIED_EPOCH_RESOLVED_TO_STEADY",
        })
        self.oldest_unresolved_demand_ns = None
        self.carried_suspicion_evidence = 0
        self.suspected_since_ns = None
        self._set_resolved_pair(item, "QUALIFIED_EPOCH_RESOLVED_TO_STEADY")
        self._set_progress_pair(item, "SYNCHRONIZE_RESOLVED_PAIR")
        self.state = "STEADY_TRACKING"

    def update(self, item: ReleasedObservation) -> dict:
        if not isinstance(item, ReleasedObservation):
            raise TypeError("Only released observations may enter the qualifier")
        if self.last_time_ns is not None and item.time_ns <= self.last_time_ns:
            raise ValueError("Strictly increasing causal observations required")
        valid = self._valid(item)
        previous_state = self.state
        command_event = self.last_command is None or item.plc_command != self.last_command
        if self.resolved_pair is None and valid and self.epoch is None and self.oldest_unresolved_demand_ns is None and abs(
            item.plc_command - item.measured_speed
        ) <= self.tracking_tolerance:
            self._set_resolved_pair(item, "DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE")
        gross = item.plc_command - self.resolved_pair.resolved_command_anchor if self.resolved_pair else None
        observable = (
            valid and gross is not None and abs(gross) >= self.material_delta
            and self._response_open(item.command_timestamp_ns, abs(gross)) is not None
        )
        demand_class = "IMMATERIAL_UPDATE"
        if command_event and observable:
            direction = 1 if gross > 0 else -1
            if self.epoch is not None and self.epoch.completion_reason is None and direction != self.direction:
                demand_class = "MATERIAL_REVERSAL"
                self._close_epoch(item, "MATERIAL_REVERSAL")
                self.epoch_events.append({
                    "time_ns": item.time_ns, "event": "CARRY_ACROSS_REVERSAL",
                    "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
                    "carried_suspicion_evidence": self.carried_suspicion_evidence,
                })
                self._start_epoch(item, direction, demand_class)
            elif self.epoch is None or self.epoch.completion_reason is not None:
                demand_class = "OBSERVABLE_MATERIAL_DEMAND"
                self._start_epoch(item, direction, demand_class)
            else:
                demand_class = "OBSERVABLE_MATERIAL_DEMAND"
                self.epoch.latest_command = item.plc_command
                self.latest_demand = max(self.latest_demand, abs(gross))
                self.epoch_events.append({
                    "time_ns": item.time_ns, "event": "SAME_DIRECTION_UPDATE",
                    "epoch_id": self.epoch.tracking_epoch_id,
                    "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
                })
        elif command_event and gross is not None and abs(gross) >= self.material_delta:
            demand_class = "NOT_OBSERVABLE_FOR_TRACKING_QUALIFICATION"
        if self.epoch is not None and self.epoch.completion_reason is None:
            self.epoch.latest_command = item.plc_command
        if command_event:
            self.last_command = item.plc_command

        qualified = False
        checkpoint_command_displacement = None
        checkpoint_measured_displacement = None
        expected = None
        if not valid:
            self.state = "INSUFFICIENT_MEASUREMENT"
        elif self.confirmed_latched:
            self.state = "TRACKING_FAULT_CONFIRMED"
        elif self.oldest_unresolved_demand_ns is None or self.epoch is None or self.progress_pair is None:
            self.state = "STEADY_TRACKING"
        else:
            pair = self.progress_pair
            assert item.measured_speed is not None and self.direction is not None
            checkpoint_command_displacement = self.direction * (item.plc_command - pair.progress_command_reference)
            checkpoint_measured_displacement = self.direction * (item.measured_speed - pair.progress_measurement_reference)
            outstanding_at_pair = max(
                0.0, self.direction * (pair.progress_command_reference - pair.progress_measurement_reference)
            )
            demand = max(0.0, checkpoint_command_displacement + outstanding_at_pair)
            expected = self._expected(demand, item.time_ns, self.oldest_unresolved_demand_ns)
            ratio = checkpoint_measured_displacement / expected if expected > 0 else None
            qualified = (
                checkpoint_measured_displacement >= self.minimum_motion
                and ratio is not None and ratio >= self.suspect_ratio
                and item.sample_ns is not None and item.sample_ns >= pair.progress_pair_ns
            )
            if qualified:
                self.qualified_progress_seen = True
                self.credited_motion += checkpoint_measured_displacement
                if abs(item.plc_command - item.measured_speed) <= self.tracking_tolerance:
                    self._resolve(item)
                else:
                    self._set_progress_pair(item, "QUALIFIED_DIRECTIONAL_PROGRESS")
                    self.state = "TRACKING_PROGRESS"
            elif expected < self.suspect_expected or item.time_ns < (
                self._response_open(self.oldest_unresolved_demand_ns, demand) or item.time_ns
            ):
                self.state = "HANDOFF_PENDING"
            else:
                if self.suspected_since_ns is None:
                    self.suspected_since_ns = item.time_ns
                deficient = expected >= self.confirm_expected and (ratio is None or ratio < self.confirm_ratio)
                if deficient and item.measurement_record_id != self.last_measurement_id:
                    self.carried_suspicion_evidence += 1
                self.state = "TRACKING_FAULT_SUSPECTED"
                if self.carried_suspicion_evidence >= self.confirm_samples:
                    self.confirmed_latched = True
                    self.confirmed_since_ns = item.time_ns
                    self.epoch.confirmed_since_ns = item.time_ns
                    self.state = "TRACKING_FAULT_CONFIRMED"
                    self._close_epoch(item, "QUALIFIED_NO_MOTION_CONFIRMED")
        if self.state != previous_state:
            self.transitions.append({
                "time_ns": item.time_ns, "from": previous_state, "to": self.state,
                "measurement_record_id": item.measurement_record_id,
            })
        if valid:
            self.last_measurement_id = item.measurement_record_id
        self.last_time_ns = item.time_ns
        record = {
            "time_ns": item.time_ns, "state": self.state, "demand_class": demand_class,
            "valid": valid, "plc_command": item.plc_command, "measured_speed": item.measured_speed,
            "measurement_record_id": item.measurement_record_id,
            "resolved_anchor_pair_id": self.resolved_pair.resolved_anchor_pair_id if self.resolved_pair else None,
            "resolved_command_anchor": self.resolved_pair.resolved_command_anchor if self.resolved_pair else None,
            "resolved_measurement_anchor": self.resolved_pair.resolved_measurement_anchor if self.resolved_pair else None,
            "progress_pair_id": self.progress_pair.progress_pair_id if self.progress_pair else None,
            "progress_command_reference": self.progress_pair.progress_command_reference if self.progress_pair else None,
            "progress_measurement_reference": self.progress_pair.progress_measurement_reference if self.progress_pair else None,
            "gross_command_demand": gross,
            "checkpoint_command_displacement": checkpoint_command_displacement,
            "checkpoint_measured_displacement": checkpoint_measured_displacement,
            "expected_motion": expected, "qualified_progress": qualified,
            "credited_motion": self.credited_motion,
            "epoch_id": self.epoch.tracking_epoch_id if self.epoch else None,
            "watch_id": f"motion-watch:{self.watch_number}" if self.oldest_unresolved_demand_ns is not None else None,
            "oldest_unresolved_demand_ns": self.oldest_unresolved_demand_ns,
            "carried_suspicion_evidence": self.carried_suspicion_evidence,
            "confirmed_latched": self.confirmed_latched,
        }
        self.records.append(record)
        return record

    def snapshot(self) -> dict:
        return {
            "state": self.state, "records": self.records, "transitions": self.transitions,
            "epoch_events": self.epoch_events, "watch_events": self.watch_events,
            "resolved_pair_events": self.resolved_pair_events,
            "progress_pair_events": self.progress_pair_events,
            "resolved_pair": asdict(self.resolved_pair) if self.resolved_pair else None,
            "progress_pair": asdict(self.progress_pair) if self.progress_pair else None,
            "confirmed_latched": self.confirmed_latched,
        }
