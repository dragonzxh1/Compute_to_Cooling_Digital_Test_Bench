"""Offline-only continuous tracking qualifier; no production Safety imports or writes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp

STATES = (
    "STEADY_TRACKING", "HANDOFF_PENDING", "TRACKING_PROGRESS",
    "TRACKING_FAULT_SUSPECTED", "TRACKING_FAULT_CONFIRMED", "INSUFFICIENT_MEASUREMENT",
)


@dataclass(frozen=True)
class ReleasedObservation:
    time_ns: int
    plc_command: float
    command_timestamp_ns: int
    measured_speed: float | None
    sample_ns: int | None
    release_ns: int | None
    quality: str
    measurement_record_id: str


@dataclass
class TrackingEpoch:
    tracking_epoch_id: str
    epoch_start_ns: int
    anchor_command: float
    latest_command: float
    anchor_measured_speed: float
    expected_direction: int
    oldest_unresolved_demand_ns: int
    response_open_ns: int
    tracking_status: str
    qualified_progress_seen: bool = False
    suspected_since_ns: int | None = None
    confirmed_since_ns: int | None = None
    measurement_record_id: str = ""
    completion_reason: str | None = None


@dataclass
class UnresolvedMotionWatch:
    watch_id: str
    watch_start_ns: int
    anchor_measured_speed: float
    cumulative_observable_demand: float
    qualified_motion_seen: bool = False
    last_valid_measurement_ns: int | None = None
    carried_suspicion_evidence: int = 0
    resolved_reason: str | None = None


class OfflineTrackingQualifier:
    """Consumes only released observations, frozen profile and frozen R5.2 classifier."""

    def __init__(self, profile: dict, r5_2_classifier: dict):
        actuator = profile["ActuatorTrackingProfile"]
        sensor = profile["SensorObservationProfile"]
        qualification = profile["TrackingQualificationProfile"]
        self.delay_ns = round(actuator["command_delay_s"]["value"] * 1e9)
        self.tau_s = actuator["lag_time_constant_s"]["value"]
        self.ramp = actuator["speed_rate_limit_per_s"]["value"]
        self.sample_ns = round(sensor["measurement_period_s"]["value"] * 1e9)
        self.release_delay_ns = round(sensor["measurement_release_delay_s"]["value"] * 1e9)
        self.max_age_ns = round(sensor["measurement_validity_limit_s"]["value"] * 1e9)
        self.material_delta = qualification["material_command_delta"]["value"]
        self.minimum_motion = qualification["minimum_observable_speed_change"]["value"]
        self.tracking_tolerance = qualification["tracking_error_tolerance"]["value"]
        frozen = qualification["suspected_rule_parameters"]["value"]
        confirm = qualification["confirmed_rule_parameters"]["value"]
        if frozen != {"expected_min": r5_2_classifier["suspect_min_expected_progress_fraction"], "ratio_below": r5_2_classifier["suspect_progress_ratio_below"]}:
            raise ValueError("R5.2 suspected rule/profile mismatch")
        if confirm != {"expected_min": r5_2_classifier["confirm_min_expected_progress_fraction"], "ratio_below": r5_2_classifier["confirm_progress_ratio_below"], "qualified_samples": r5_2_classifier["confirm_consecutive_qualified_samples"]}:
            raise ValueError("R5.2 confirmed rule/profile mismatch")
        self.suspect_expected = frozen["expected_min"]
        self.suspect_ratio = frozen["ratio_below"]
        self.confirm_expected = confirm["expected_min"]
        self.confirm_ratio = confirm["ratio_below"]
        self.confirm_samples = confirm["qualified_samples"]
        self.state = "STEADY_TRACKING"
        self.epoch = None
        self.watch = None
        self.last_command = None
        self.last_time_ns = None
        self.last_measurement_id = None
        self.epoch_number = 0
        self.watch_number = 0
        self.transitions = []
        self.epoch_events = []
        self.watch_events = []
        self.records = []
        self.confirmed_latched = False
        self.restored_motion_after_confirmation = False

    def _expected(self, magnitude: float, time_ns: int, start_ns: int) -> float:
        active = max(0.0, (time_ns - start_ns - self.delay_ns) / 1e9)
        return min(self.ramp * active, magnitude * (1 - exp(-active / self.tau_s)))

    def _response_open(self, command_ns: int, magnitude: float) -> int | None:
        if magnitude <= self.minimum_motion:
            return None
        sample = ((command_ns + self.delay_ns + self.sample_ns - 1) // self.sample_ns) * self.sample_ns
        while self._expected(magnitude, sample, command_ns) < self.minimum_motion:
            sample += self.sample_ns
        return sample + self.release_delay_ns

    def _valid(self, item: ReleasedObservation) -> bool:
        return (
            item.measured_speed is not None and item.sample_ns is not None and item.release_ns is not None
            and item.quality == "VALID" and item.release_ns <= item.time_ns
            and 0 <= item.time_ns - item.sample_ns <= self.max_age_ns
        )

    def _new_epoch(self, item: ReleasedObservation, anchor_command: float, direction: int, *, reason: str) -> None:
        self.epoch_number += 1
        oldest = self.watch.watch_start_ns if self.watch is not None else item.command_timestamp_ns
        magnitude = abs(item.plc_command - anchor_command)
        opened = self._response_open(item.command_timestamp_ns, magnitude)
        if opened is None:
            raise ValueError("Unobservable demand cannot start epoch")
        self.epoch = TrackingEpoch(
            f"tracking-epoch:{self.epoch_number}", item.command_timestamp_ns, anchor_command,
            item.plc_command, item.measured_speed, direction, oldest, opened, "HANDOFF_PENDING",
            measurement_record_id=item.measurement_record_id,
        )
        self.epoch_events.append({"time_ns": item.time_ns, "event": "START", "reason": reason, "epoch_id": self.epoch.tracking_epoch_id,
                                  "oldest_unresolved_demand_ns": oldest, "expected_direction": direction})
        if self.watch is None:
            self.watch_number += 1
            self.watch = UnresolvedMotionWatch(f"motion-watch:{self.watch_number}", item.command_timestamp_ns,
                                               item.measured_speed, magnitude, last_valid_measurement_ns=item.sample_ns)
            self.watch_events.append({"time_ns": item.time_ns, "event": "START", "watch_id": self.watch.watch_id,
                                      "watch_start_ns": self.watch.watch_start_ns})

    def _close_epoch(self, item: ReleasedObservation, reason: str) -> None:
        if self.epoch is not None and self.epoch.completion_reason is None:
            self.epoch.completion_reason = reason
            self.epoch_events.append({"time_ns": item.time_ns, "event": "CLOSE", "epoch_id": self.epoch.tracking_epoch_id,
                                      "reason": reason})

    def _resolve_watch(self, item: ReleasedObservation, reason: str) -> None:
        if self.watch is not None:
            self.watch.qualified_motion_seen = True
            self.watch.resolved_reason = reason
            self.watch_events.append({"time_ns": item.time_ns, "event": "RESOLVE", "watch_id": self.watch.watch_id,
                                      "reason": reason})
            self.watch = None

    def update(self, item: ReleasedObservation) -> dict:
        if not isinstance(item, ReleasedObservation):
            raise TypeError("Only released observations may enter the qualifier")
        if self.last_time_ns is not None and item.time_ns <= self.last_time_ns:
            raise ValueError("Strictly increasing causal observations required")
        valid = self._valid(item)
        command_event = self.last_command is None or item.plc_command != self.last_command
        reference = item.measured_speed if self.last_command is None else self.last_command
        step = None if reference is None else item.plc_command - reference
        material = bool(command_event and valid and step is not None and abs(step) >= self.material_delta
                        and self._response_open(item.command_timestamp_ns, abs(step)) is not None)
        demand_class = "IMMATERIAL_UPDATE"
        if command_event and step is not None and abs(step) >= self.material_delta and not material:
            demand_class = "NOT_OBSERVABLE_FOR_TRACKING_QUALIFICATION"
        if material:
            direction = 1 if step > 0 else -1
            demand_class = "MATERIAL_REVERSAL" if self.epoch is not None and direction != self.epoch.expected_direction else "OBSERVABLE_MATERIAL_DEMAND"
            if demand_class == "MATERIAL_REVERSAL":
                prior_motion = self.watch is None or self.watch.qualified_motion_seen
                self._close_epoch(item, "MATERIAL_REVERSAL")
                if prior_motion:
                    self._resolve_watch(item, "QUALIFIED_PRIOR_MOTION")
                else:
                    self.watch_events.append({"time_ns": item.time_ns, "event": "CARRY_ACROSS_REVERSAL",
                                              "watch_id": self.watch.watch_id, "watch_start_ns": self.watch.watch_start_ns,
                                              "carried_suspicion_evidence": self.watch.carried_suspicion_evidence})
                self._new_epoch(item, reference, direction, reason="REVERSAL")
            elif self.epoch is None or self.epoch.completion_reason is not None or self.watch is None:
                self._new_epoch(item, reference, direction, reason="MATERIAL_DEMAND")
            else:
                self.epoch.latest_command = item.plc_command
                self.watch.cumulative_observable_demand = max(
                    self.watch.cumulative_observable_demand,
                    abs(item.plc_command - self.watch.anchor_measured_speed),
                )
                self.epoch_events.append({"time_ns": item.time_ns, "event": "SAME_DIRECTION_UPDATE",
                                          "epoch_id": self.epoch.tracking_epoch_id,
                                          "oldest_unresolved_demand_ns": self.watch.watch_start_ns})
        elif self.epoch is not None:
            self.epoch.latest_command = item.plc_command
        if command_event:
            self.last_command = item.plc_command
        previous_state = self.state
        if not valid:
            self.state = "INSUFFICIENT_MEASUREMENT"
        elif self.confirmed_latched:
            if self.watch is not None and abs(item.measured_speed - self.watch.anchor_measured_speed) >= self.minimum_motion:
                self.restored_motion_after_confirmation = True
            self.state = "TRACKING_FAULT_CONFIRMED"
        elif self.watch is None:
            if self.epoch is not None and self.epoch.qualified_progress_seen and abs(self.epoch.latest_command - item.measured_speed) <= self.tracking_tolerance:
                self._close_epoch(item, "STEADY_WITHIN_TRACKING_TOLERANCE")
                self.state = "STEADY_TRACKING"
            elif self.epoch is not None and self.epoch.qualified_progress_seen:
                self.state = "TRACKING_PROGRESS"
            else:
                self.state = "STEADY_TRACKING"
        else:
            self.watch.last_valid_measurement_ns = item.sample_ns
            epoch_progress = self.epoch.expected_direction * (item.measured_speed - self.epoch.anchor_measured_speed)
            epoch_expected = self._expected(abs(self.epoch.latest_command - self.epoch.anchor_command), item.time_ns, self.epoch.epoch_start_ns)
            epoch_ratio = epoch_progress / epoch_expected if epoch_expected > 0 else None
            directed_motion = epoch_progress >= self.minimum_motion and epoch_ratio is not None and epoch_ratio >= self.suspect_ratio
            watch_motion = max(0.0, epoch_progress)
            watch_expected = self._expected(self.watch.cumulative_observable_demand, item.time_ns, self.watch.watch_start_ns)
            watch_ratio = watch_motion / watch_expected if watch_expected > 0 else None
            if directed_motion:
                self.epoch.qualified_progress_seen = True
                self._resolve_watch(item, "QUALIFIED_DIRECTIONAL_PROGRESS")
                self.state = "TRACKING_PROGRESS"
            elif item.time_ns < self._response_open(self.watch.watch_start_ns, self.watch.cumulative_observable_demand) or watch_expected < self.suspect_expected:
                self.state = "HANDOFF_PENDING"
            else:
                if self.epoch.suspected_since_ns is None:
                    self.epoch.suspected_since_ns = item.time_ns
                deficient = watch_expected >= self.confirm_expected and (watch_ratio is None or watch_ratio < self.confirm_ratio)
                self.watch.carried_suspicion_evidence = self.watch.carried_suspicion_evidence + 1 if deficient and item.measurement_record_id != self.last_measurement_id else self.watch.carried_suspicion_evidence
                self.state = "TRACKING_FAULT_SUSPECTED"
                if self.watch.carried_suspicion_evidence >= self.confirm_samples:
                    self.confirmed_latched = True
                    self.epoch.confirmed_since_ns = item.time_ns
                    self.state = "TRACKING_FAULT_CONFIRMED"
                    self._close_epoch(item, "QUALIFIED_NO_MOTION_CONFIRMED")
        if self.state != previous_state:
            self.transitions.append({"time_ns": item.time_ns, "from": previous_state, "to": self.state,
                                     "measurement_record_id": item.measurement_record_id})
        if valid:
            self.last_measurement_id = item.measurement_record_id
        self.last_time_ns = item.time_ns
        record = {"time_ns": item.time_ns, "state": self.state, "demand_class": demand_class,
                  "epoch_id": self.epoch.tracking_epoch_id if self.epoch else None,
                  "epoch_start_ns": self.epoch.epoch_start_ns if self.epoch else None,
                  "expected_direction": self.epoch.expected_direction if self.epoch else None,
                  "watch_id": self.watch.watch_id if self.watch else None,
                  "watch_start_ns": self.watch.watch_start_ns if self.watch else None,
                  "carried_suspicion_evidence": self.watch.carried_suspicion_evidence if self.watch else 0,
                  "valid": valid, "measurement_record_id": item.measurement_record_id,
                  "confirmed_latched": self.confirmed_latched,
                  "restored_motion_after_confirmation": self.restored_motion_after_confirmation}
        self.records.append(record)
        return record

    def snapshot(self) -> dict:
        return {"state": self.state, "records": self.records, "transitions": self.transitions,
                "epoch_events": self.epoch_events, "watch_events": self.watch_events,
                "epoch": asdict(self.epoch) if self.epoch else None,
                "watch": asdict(self.watch) if self.watch else None,
                "confirmed_latched": self.confirmed_latched,
                "restored_motion_after_confirmation": self.restored_motion_after_confirmation}
