"""Offline startup qualification candidate; observed position is not a resolved command."""

from dataclasses import asdict, dataclass, replace
from math import isfinite

from v0_2.examples.phase5_r5_2_1r4_2_directional_engine import (
    DirectionalObligationTrackingQualifier,
    DirectionalTrackingObligation,
)


@dataclass(frozen=True)
class StartupObservation:
    command: float
    measured_speed: float
    sample_ns: int
    measurement_record_id: str


class StartupTrackingQualifier(DirectionalObligationTrackingQualifier):
    def __init__(self, profile, classifier):
        super().__init__(profile, classifier)
        self.startup_observation = None
        self.startup_outage_direction = None
        self.startup_demand_suspended = False
        self.published_progress_epoch_id = None

    def _valid(self, item):
        return (super()._valid(item) and isfinite(item.measured_speed)
                and item.sample_ns <= item.release_ns)

    def _process_invalid(self, item):
        super()._process_invalid(item)
        if self.resolved_pair is not None or self.startup_observation is None or self.confirmed_latched:
            return
        net = item.plc_command - self.startup_observation.measured_speed
        if abs(net) < self.material_delta:
            return
        direction = 1 if net > 0 else -1
        prior = self.startup_outage_direction
        prior_direction = prior["direction"] if prior else self.direction
        if direction != prior_direction:
            self.startup_outage_direction = {
                "direction": direction, "established_ns": item.command_timestamp_ns,
                "measurement_record_id": self.startup_observation.measurement_record_id,
            }
            self._close_epoch(item, "STARTUP_OUTAGE_DIRECTION_SUPERSEDED")

    def _resolve(self, item):
        epoch_id = self.epoch.tracking_epoch_id
        progress_already_published = epoch_id == self.published_progress_epoch_id
        super()._resolve(item)
        self.startup_outage_direction = None
        if not progress_already_published:
            # Resolution and its paired-anchor bookkeeping remain on this
            # qualified sample. Publish the real progress milestone once;
            # the next sample is evaluated normally, including invalid data
            # or a new command, rather than forcing a delayed steady state.
            self.state = "TRACKING_PROGRESS"

    def _expected(self, magnitude, time_ns, start_ns):
        if self.startup_outage_direction is not None:
            start_ns = max(start_ns, self.startup_outage_direction["established_ns"])
        pair = self.progress_pair
        if pair is not None and pair.update_reason == "QUALIFIED_DIRECTIONAL_PROGRESS":
            # Measured displacement is relative to this checkpoint, so its
            # expected displacement must cover the same interval. Qualified
            # motion advances this clock; command updates and outages do not.
            # The actuator is already responding: do not grant another delay.
            start_ns = max(start_ns, pair.progress_pair_ns - self.delay_ns)
        return super()._expected(magnitude, time_ns, start_ns)

    def update(self, item):
        if self.last_time_ns is not None and item.time_ns <= self.last_time_ns:
            raise ValueError("Strictly increasing causal observations required")
        if self.resolved_pair is None and self._valid(item):
            if (self.startup_observation is not None and not self.confirmed_latched
                    and self.epoch is not None and self.epoch.completion_reason is None
                    and abs(item.plc_command - self.startup_observation.measured_speed) < self.material_delta
                    and abs(item.measured_speed - self.startup_observation.measured_speed) < self.minimum_motion):
                # No current motion is requested. Retain actual fault evidence,
                # if any, but do not evaluate the old direction while demand
                # is absent. A new demand gets its own response interval.
                proven = self.carried_suspicion_evidence > 0
                reason = "STARTUP_DEMAND_SUSPENDED_WITH_EVIDENCE" if proven else "STARTUP_DEMAND_CANCELED_NO_EVIDENCE"
                self._close_epoch(item, reason)
                if not proven:
                    self.watch_events.append({
                        "time_ns": item.time_ns, "event": "CANCEL",
                        "watch_id": f"motion-watch:{self.watch_number}",
                        "reason": reason,
                    })
                self.epoch = None
                self.progress_pair = None
                if not proven:
                    self.oldest_unresolved_demand_ns = None
                    self.startup_observation = None
                else:
                    self.startup_demand_suspended = True
                self.direction = None
                self.directional_obligation = None
                self.startup_outage_direction = None
            if self.startup_observation is None:
                error = item.plc_command - item.measured_speed
                if abs(error) >= self.material_delta:
                    self.startup_observation = StartupObservation(
                        item.plc_command, item.measured_speed, item.sample_ns,
                        item.measurement_record_id,
                    )
                    # No evidence predates the first observed position. In particular,
                    # a late first sensor sample cannot prove earlier non-response.
                    observed = replace(item, command_timestamp_ns=max(
                        item.command_timestamp_ns, item.sample_ns))
                    self._start_epoch(observed, 1 if error > 0 else -1,
                                      "UNRESOLVED_STARTUP_DEMAND")
                    self.epoch.anchor_command = item.plc_command
            elif (not self.confirmed_latched and (self.epoch is None or
                  self.epoch.completion_reason in (None, "STARTUP_OUTAGE_DIRECTION_SUPERSEDED"))):
                net = item.plc_command - self.startup_observation.measured_speed
                direction = 1 if net > 0 else -1
                if abs(net) >= self.material_delta and (
                    self.epoch is None or direction != self.direction or self.epoch.completion_reason is not None
                ):
                    recovering = self.measurement_unavailable_since_ns is not None
                    if self.epoch is not None:
                        self._close_epoch(item, "STARTUP_DIRECTION_SUPERSEDED")
                    context = self.startup_outage_direction
                    if recovering and context and context["direction"] == direction:
                        observed = replace(item, command_timestamp_ns=context["established_ns"])
                    else:
                        observed = item
                        self.startup_outage_direction = None
                    self._start_epoch(observed, direction,
                                      "OUTAGE_DIRECTION_RECOVERY" if recovering else "MATERIAL_REVERSAL")
                    self.epoch.anchor_command = item.plc_command
                    if self.startup_demand_suspended:
                        self.directional_obligation = DirectionalTrackingObligation(
                            direction, item.command_timestamp_ns, item.plc_command,
                            f"startup-unresolved:{self.startup_observation.measurement_record_id}",
                            self.progress_pair.progress_pair_id if self.progress_pair else None,
                        )
                        self.startup_demand_suspended = False
        record = super().update(item)
        if record["state"] == "TRACKING_PROGRESS" and record["epoch_id"] is not None:
            self.published_progress_epoch_id = record["epoch_id"]
        record["startup_observation"] = (
            asdict(self.startup_observation) if self.startup_observation else None
        )
        record["baseline_resolved"] = self.resolved_pair is not None
        record["startup_demand_suspended"] = self.startup_demand_suspended
        record["startup_outage_direction"] = (
            dict(self.startup_outage_direction) if self.startup_outage_direction else None
        )
        return record
