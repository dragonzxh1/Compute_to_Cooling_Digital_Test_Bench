"""Offline-only R1 net-command-demand adapter over frozen R5.2.1R semantics."""

from __future__ import annotations

from dataclasses import replace

from v0_2.examples.phase5_r5_2_1r_semantic_engine import (
    OfflineTrackingQualifier,
    ReleasedObservation,
)


class CumulativeTrackingQualifier(OfflineTrackingQualifier):
    """Add a resolved-command anchor without changing R5.2.1R fault rules."""

    def __init__(self, profile: dict, r5_2_classifier: dict):
        super().__init__(profile, r5_2_classifier)
        self.qualified_command_anchor: float | None = None
        self.qualified_command_anchor_ns: int | None = None
        self.qualified_measurement_anchor: float | None = None
        self.anchor_source_epoch_id: str | None = None
        self.anchor_events: list[dict] = []

    def _advance_anchor(self, item: ReleasedObservation, reason: str) -> None:
        previous = self.qualified_command_anchor
        self.qualified_command_anchor = item.plc_command
        self.qualified_command_anchor_ns = item.time_ns
        self.qualified_measurement_anchor = item.measured_speed
        self.anchor_source_epoch_id = self.epoch.tracking_epoch_id if self.epoch else None
        self.anchor_events.append({
            "time_ns": item.time_ns, "anchor_update_reason": reason,
            "previous_anchor": previous, "new_anchor": item.plc_command,
            "anchor_source_epoch_id": self.anchor_source_epoch_id,
        })

    def update(self, item: ReleasedObservation) -> dict:
        valid = self._valid(item)
        if (self.last_command is None and self.qualified_command_anchor is None
                and valid and self.epoch is None
                and abs(item.plc_command - item.measured_speed) <= self.tracking_tolerance):
            # First directly observed PLC command and released speed, not a
            # fictitious pre-takeover PLC command or raw actuator state.
            self._advance_anchor(item, "DIRECTLY_OBSERVED_INITIAL_STEADY_BASELINE")

        anchor_before = self.qualified_command_anchor
        net = item.plc_command - anchor_before if anchor_before is not None else None
        actual_last_command = self.last_command
        command_event = actual_last_command is None or item.plc_command != actual_last_command
        has_unresolved_watch = self.watch is not None
        can_use_net = (anchor_before is not None and command_event
                       and (self.epoch is None or self.epoch.completion_reason is not None
                            or has_unresolved_watch))

        if can_use_net and valid:
            # Only this event uses the resolved anchor as demand reference.
            # The superclass then retains its frozen progress/fault rules.
            self.last_command = anchor_before
        elif (can_use_net and not valid and abs(net) >= self.material_delta
              and self._response_open(item.command_timestamp_ns, abs(net)) is not None):
            if self.watch is None and self.qualified_measurement_anchor is not None:
                remembered = replace(item, measured_speed=self.qualified_measurement_anchor)
                self._new_epoch(remembered, anchor_before, 1 if net > 0 else -1,
                                reason="NET_DEMAND_DURING_INVALID_MEASUREMENT")
            elif self.watch is not None:
                self.epoch.latest_command = item.plc_command
                self.watch.cumulative_observable_demand = max(
                    self.watch.cumulative_observable_demand,
                    abs(item.plc_command - self.watch.anchor_measured_speed),
                )

        record = super().update(item)
        if (valid and self.state == "STEADY_TRACKING" and self.epoch is not None
                and self.epoch.qualified_progress_seen
                and self.epoch.completion_reason == "STEADY_WITHIN_TRACKING_TOLERANCE"
                and self.anchor_source_epoch_id != self.epoch.tracking_epoch_id):
            self._advance_anchor(item, "QUALIFIED_EPOCH_RESOLVED_TO_STEADY")

        record["qualified_command_anchor"] = self.qualified_command_anchor
        record["qualified_command_anchor_ns"] = self.qualified_command_anchor_ns
        record["qualified_measurement_anchor"] = self.qualified_measurement_anchor
        record["anchor_source_epoch_id"] = self.anchor_source_epoch_id
        record["net_command_demand"] = net
        record["net_demand_classification"] = record["demand_class"]
        record["cumulative_demand_trigger_ns"] = (
            self.epoch.epoch_start_ns if self.epoch is not None
            and record["demand_class"] == "OBSERVABLE_MATERIAL_DEMAND" else None
        )
        record["plc_command"] = item.plc_command
        record["measured_speed"] = item.measured_speed
        record["watch_active"] = self.watch is not None
        return record

    def snapshot(self) -> dict:
        result = super().snapshot()
        result["qualified_command_anchor"] = self.qualified_command_anchor
        result["qualified_command_anchor_ns"] = self.qualified_command_anchor_ns
        result["qualified_measurement_anchor"] = self.qualified_measurement_anchor
        result["anchor_source_epoch_id"] = self.anchor_source_epoch_id
        result["anchor_events"] = self.anchor_events
        return result
