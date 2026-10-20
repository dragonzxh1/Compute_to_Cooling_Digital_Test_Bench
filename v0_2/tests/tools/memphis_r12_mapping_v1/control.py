"""Versioned R12 intent state machines consuming released test measurements.

No M1/PLC imports. Requests are NOT issue receipts. All timing/freshness policy
not specified by R12 must be provided explicitly and remains engineering OPEN.
"""
from dataclasses import dataclass
from math import isfinite
from .topology import PRIMARY_NETWORK_ID, SECONDARY_NETWORK_ID, cdu_name, isolation_errors, connectivity, path, enabled_edges


@dataclass(frozen=True)
class UnitPolicy:
    freshness_s: float
    max_sample_gap_s: float
    cold_return_limit_C: float
    test_only: bool = True

    def __post_init__(self):
        if not self.test_only or not (0 < self.freshness_s <= 1 and 0 < self.max_sample_gap_s <= 1 and 0 < self.cold_return_limit_C <= 45):
            raise ValueError("TEST_POLICY_ONLY_ENGINEERING_TIMING_UNAPPROVED")


def released(obs, now, policy):
    try:
        return (obs["provenance"] == "SYNTHETIC_RELEASED_UNIT_MEASUREMENTS" and
                0 <= obs["sample_s"] <= obs["release_s"] <= now and
                now - obs["sample_s"] <= policy.freshness_s and
                obs["channels_independent_fixture"] is True)
    except (KeyError, TypeError):
        return False


def finite_pair(obs, key):
    vals = obs.get(key, [])
    return len(vals) == 2 and all(type(v) in (float, int) and isfinite(v) for v in vals)


class T2Controller:
    def __init__(self, graph, unit, primary, old_secondary, new_secondary, policy):
        if type(primary) is not PRIMARY_NETWORK_ID or type(old_secondary) is not SECONDARY_NETWORK_ID or type(new_secondary) is not SECONDARY_NETWORK_ID:
            raise TypeError("THREE_IDENTITY_SPACES_REQUIRED")
        if old_secondary == new_secondary or unit not in (1, 2, 3):
            raise ValueError("INVALID_T2_SCOPE")
        self.g, self.unit, self.primary = graph, unit, primary
        self.old, self.new, self.policy = old_secondary, new_secondary, policy
        self.state = "OPEN_NEW_PRIMARY"; self.stable_since = None
        self.previous_sample = None; self.overlap_since = None
        self.events = []; self.revoke_sample = None; self.stop_sample = None
        self.request = {"primary_network": primary.value, "old_CDU": cdu_name(unit, old_secondary),
            "new_CDU": cdu_name(unit, new_secondary), "new_primary_open": True,
            "new_rack_open": False, "old_rack_open": True, "old_stop_requested": False,
            "master_request": "OLD", "LP_B_START_REQUESTED": False,
            "provenance": "UNIT_CONTROL_REQUEST_NOT_PLC_RECEIPT"}

    def step(self, obs, now):
        valid = released(obs, now, self.policy)
        perms = {k: False for k in ("TEMP_MATCH_VALID", "PRESSURE_MATCH_VALID", "STABLE_5S_VALID",
             "PRESSURE_MASTER_TRANSFER_VALID", "OVERLAP_TIMER_VALID", "SENSOR_FRESHNESS_VALID",
             "VALVE_FEEDBACK_VALID", "FLOW_ESTABLISHED_VALID")}
        perms["SENSOR_FRESHNESS_VALID"] = valid
        errors = []
        if not valid:
            self.stable_since = None
            errors.append("STALE_INVALID_OR_UNRELEASED_MEASUREMENTS")
        else:
            errors += isolation_errors(self.g, obs["valves"])
            if obs["primary_network"] != self.primary.value:
                errors.append("T2_CANNOT_CHANGE_PRIMARY_NETWORK")
            if obs["sample_s"] <= (self.previous_sample if self.previous_sample is not None else -1):
                errors.append("NONINCREASING_SAMPLE")
            if self.previous_sample is not None and obs["sample_s"] - self.previous_sample > self.policy.max_sample_gap_s:
                self.stable_since = None
            self.previous_sample = obs["sample_s"]
            if len(obs.get("pressure_masters", [])) > 1:
                errors.append("MULTIPLE_PRESSURE_MASTERS")
        if errors:
            return self._record(obs, now, perms, errors, "HOLD_REQUEST_LOAD_PROTECTION")
        c = cdu_name(self.unit, self.new); a = cdu_name(self.unit, self.old)
        n = self.primary.value
        v = obs["valves"]; p = obs["pumps"]
        new_primary = (v.get(c+f"-P1-CV-{n}S") is True and v.get(c+f"-P1-CV-{n}R") is True and
                       all(v.get(c+f"-P1-CV-{other}{d}") is False for other in ("A", "B") if other != n for d in ("S", "R")))
        primary_flow = finite_pair(obs, "new_primary_flow_m3_h") and min(obs["new_primary_flow_m3_h"]) > 0
        temp = finite_pair(obs, "delta_T_K") and max(abs(x) for x in obs["delta_T_K"]) <= 2
        pressure = finite_pair(obs, "delta_p_kPa") and max(abs(x) for x in obs["delta_p_kPa"]) <= 5
        perms["TEMP_MATCH_VALID"] = temp; perms["PRESSURE_MATCH_VALID"] = pressure
        if temp and pressure and new_primary and primary_flow:
            if self.stable_since is None:
                self.stable_since = obs["sample_s"]
        else:
            self.stable_since = None
        perms["STABLE_5S_VALID"] = self.stable_since is not None and obs["sample_s"] - self.stable_since >= 5
        perms["OVERLAP_TIMER_VALID"] = self.overlap_since is None or now - self.overlap_since <= 30
        if not perms["OVERLAP_TIMER_VALID"]:
            self.state = "OVERLAP_TIMEOUT_HOLD"
            return self._record(obs, now, perms, ["OVERLAP_EXCEEDS_30S"], "HOLD_REQUEST_LOAD_PROTECTION")
        old_rack_closed = all(v.get(f"G01-U{self.unit}-R{r:02d}-CV-{self.old.value}{d}") is False
                              for r in range(1, 7) for d in ("S", "R"))
        new_rack_open = all(v.get(f"G01-U{self.unit}-R{r:02d}-CV-{self.new.value}{d}") is True
                           for r in range(1, 7) for d in ("S", "R"))
        old_closed = (old_rack_closed and v.get(a + "-P2-XV-SUP") is False and v.get(a + "-P2-XV-RET") is False and
                      all(v.get(a + f"-P1-CV-{net}{d}") is False for net in ("A", "B") for d in ("S", "R")))
        new_p2_open = v.get(c + "-P2-XV-SUP") is True and v.get(c + "-P2-XV-RET") is True
        proof = connectivity(self.g, dict(valves=v, pumps=p, primary_network=n, secondary_network=self.new.value))
        local = proof["units"][self.unit-1]
        paths = local["primary_connected"] and all(r["connected"] for r in local["racks"])
        flow = (finite_pair(obs, "new_secondary_flow_m3_h") and min(obs["new_secondary_flow_m3_h"]) > 0 and
                len(obs.get("rack_flow_m3_h", [])) == 6 and
                all(len(x) == 2 and all(type(q) in (int, float) and isfinite(q) and q > 0 for q in x) for x in obs["rack_flow_m3_h"]))
        thermal = (finite_pair(obs, "new_secondary_temperature_C") and max(obs["new_secondary_temperature_C"]) <= 45 and
                   len(obs.get("rack_temperature_C", [])) == 6 and all(len(x)==2 and all(type(q) in (int,float) and isfinite(q) and q<=45 for q in x) for x in obs["rack_temperature_C"]))
        perms["VALVE_FEEDBACK_VALID"] = new_primary and new_rack_open and new_p2_open
        perms["FLOW_ESTABLISHED_VALID"] = primary_flow and flow and paths
        masters = obs["pressure_masters"]
        if self.state == "OPEN_NEW_PRIMARY" and new_primary and primary_flow:
            self.state = "WAIT_SECONDARY_MATCH"
        elif self.state == "WAIT_SECONDARY_MATCH" and perms["STABLE_5S_VALID"]:
            self.request["new_rack_open"] = True; self.overlap_since = now
            self.state = "OVERLAP_WAIT_FLOW"
        elif self.state == "OVERLAP_WAIT_FLOW" and perms["VALVE_FEEDBACK_VALID"] and perms["FLOW_ESTABLISHED_VALID"]:
            self.request["master_request"] = "NONE"; self.request["old_stop_requested"] = True
            self.stop_sample = obs["sample_s"]; self.state = "WAIT_OLD_STOP_AND_REVOKE"
        elif self.state == "WAIT_OLD_STOP_AND_REVOKE":
            stopped = finite_pair(obs, "old_pump_speed_pct") and max(abs(x) for x in obs["old_pump_speed_pct"]) == 0
            if not masters and stopped and obs.get("old_master_revoked") is True and obs["sample_s"] > self.stop_sample:
                self.revoke_sample = obs["sample_s"]; self.request["old_rack_open"] = False
                self.request["old_primary_open"] = False
                self.state = "WAIT_OLD_ISOLATION"
        elif self.state == "WAIT_OLD_ISOLATION" and old_closed and not masters and obs["sample_s"] > self.revoke_sample:
            self.request["master_request"] = c; self.state = "WAIT_NEW_MASTER"
        elif self.state == "WAIT_NEW_MASTER":
            master_ok = masters == [c] and old_closed and obs.get("old_master_revoked") is True
            perms["PRESSURE_MASTER_TRANSFER_VALID"] = master_ok
            if all(perms.values()) and thermal:
                self.state = "COMPLETED_UNIT_INTENT_ONLY"
        if self.state == "COMPLETED_UNIT_INTENT_ONLY":
            perms["PRESSURE_MASTER_TRANSFER_VALID"] = masters == [c] and old_closed
            if not all(perms.values()) or not thermal:
                self.state = "COMPLETION_REVOKED_HOLD"
        return self._record(obs, now, perms, [], "NOT_READY" if self.state != "COMPLETED_UNIT_INTENT_ONLY" else "UNIT_READY_NOT_DYNAMIC_READY")

    def _record(self, obs, now, perms, errors, verdict):
        row = dict(time_s=now, sample_s=obs.get("sample_s"), release_s=obs.get("release_s"),
            measurement_id=obs.get("id"), state=self.state, command=dict(self.request),
            valve_actuals=obs.get("valves"), pump_actuals=obs.get("pumps"),
            permissives=perms, errors=errors, verdict=verdict,
            primary_flow=obs.get("new_primary_flow_m3_h"), secondary_flow=obs.get("new_secondary_flow_m3_h"),
            rack_flow=obs.get("rack_flow_m3_h"), masters=obs.get("pressure_masters"),
            evidence_class="SYNTHETIC_STATE_MACHINE_UNIT_EVIDENCE_NOT_PLC_ISSUE")
        self.events.append(row)
        return row


class T1Controller:
    def __init__(self, primary, cdu_identities, old_source, new_source):
        if type(primary) is not PRIMARY_NETWORK_ID or old_source == new_source:
            raise ValueError("T1_SCOPE")
        self.primary, self.identities = primary, tuple(cdu_identities)
        self.old, self.new = old_source, new_source

    def complete(self, g, obs, now, policy):
        if not released(obs, now, policy) or isolation_errors(g, obs["valves"]):
            return False
        n = self.primary.value; edges = enabled_edges(g, obs["valves"], obs["pumps"])
        return (tuple(obs["CDU_IDENTITY"]) == self.identities and obs["primary_network"] == n and
                finite_pair(obs,"source_return_temperature_C") and max(obs["source_return_temperature_C"]) <= policy.cold_return_limit_C and
                finite_pair(obs, "source_flow_m3_h") and min(obs["source_flow_m3_h"]) > 0 and
                path(edges, f"G01-BT-{n}:TOP_SOURCE", f"G01-{self.new}:IN") is not None and
                path(edges, f"G01-{self.new}:OUT", f"G01-BT-{n}:BOTTOM_SOURCE") is not None and
                all(obs["valves"].get(f"G01-{self.old}-CV-{n}{d}") is False for d in ("S", "R")))


class RechargeController:
    """Shared source A->B segment; LP-A requests unchanged. No reserve model."""
    def __init__(self, graph, old, target, source, policy):
        if type(old) is not PRIMARY_NETWORK_ID or type(target) is not PRIMARY_NETWORK_ID or old == target:
            raise TypeError("RECHARGE_PRIMARY_SPACES")
        self.g, self.old, self.target, self.source, self.policy = graph, old.value, target.value, source, policy
        self.state = "WAIT_STOP_PROOF"; self.history = []; self.last_sample = -1
        self.command = {"source_pumps": "STOP", "source_network": old.value, "load_network": old.value,
                        "source_pair_open": False, "LP_RUNNING_NETWORK_UNCHANGED": True}

    def step(self, obs, now):
        reason = "WAIT_REQUIRED_PROOF"
        if not released(obs, now, self.policy) or obs["sample_s"] <= self.last_sample:
            reason = "INVALID_RELEASE_OR_SAMPLE"
        elif isolation_errors(self.g, obs["valves"]):
            reason = "PRIMARY_CROSS_CONNECT_REFUSED"
        else:
            self.last_sample = obs["sample_s"]
            v, p = obs["valves"], obs["pumps"]
            stop = obs.get("source_pump_zero_speed_proofs", {})
            stopped = all(stop.get(f"G01-SP{i:02d}") is True and p.get(f"G01-SP{i:02d}") is False for i in range(1,5))
            old_closed = all(v.get(f"G01-SRC-{d}-{self.old}") is False for d in ("H", "S")) and all(
                v.get(f"G01-{src}-CV-{self.old}{d}") is False for src in ("D1", "D2", "W1", "W2") for d in ("S", "R"))
            target_open = all(v.get(f"G01-SRC-{d}-{self.target}") is True for d in ("H", "S")) and all(
                v.get(f"G01-{self.source}-CV-{self.target}{d}") is True for d in ("S", "R"))
            if self.state == "WAIT_STOP_PROOF" and stopped and obs.get("running_tank_budget_permit") is True:
                self.state = "WAIT_OLD_CLOSED"; self.command["close_old_network"] = True
            elif self.state == "WAIT_OLD_CLOSED" and stopped and old_closed:
                self.state = "WAIT_TARGET_PATH"; self.command.update(source_network=self.target, source_pair_open=True)
            elif self.state == "WAIT_TARGET_PATH" and stopped and old_closed and target_open and obs.get("suction_liquid_permit") is True:
                self.state = "WAIT_ACTUAL_FLOW"; self.command["source_pumps"] = "START"
            elif self.state in ("WAIT_ACTUAL_FLOW", "WAIT_COLD_RETURN", "WAIT_RESERVE_PROOF"):
                e = enabled_edges(self.g, v, p)
                hydraulic = (old_closed and target_open and finite_pair(obs, "source_flow_m3_h") and min(obs["source_flow_m3_h"]) > 0 and
                    path(e, f"G01-BT-{self.target}:TOP_SOURCE", f"G01-{self.source}:IN") is not None and
                    path(e, f"G01-{self.source}:OUT", f"G01-BT-{self.target}:BOTTOM_SOURCE") is not None)
                if not hydraulic:
                    reason = "NO_ACTUAL_TARGET_HYDRAULIC_PATH"
                elif self.state == "WAIT_ACTUAL_FLOW":
                    self.state = "WAIT_COLD_RETURN"
                elif self.state == "WAIT_COLD_RETURN" and finite_pair(obs,"source_return_temperature_C") and max(obs["source_return_temperature_C"]) <= self.policy.cold_return_limit_C:
                    self.state = "WAIT_RESERVE_PROOF"
                elif self.state == "WAIT_RESERVE_PROOF" and obs.get("independent_target_reserve_proof") is True:
                    self.state = "TARGET_RESERVE_PROVEN_UNIT_FIXTURE_ONLY"
            # No claim of A restored or dual ready just because B charging ended.
        row = dict(state=self.state, command=dict(self.command), reason=reason, sample_s=obs.get("sample_s"),
            valve_actuals=obs.get("valves"), pump_actuals=obs.get("pumps"),
            B_RECHARGE_DONE=self.state == "TARGET_RESERVE_PROVEN_UNIT_FIXTURE_ONLY" and self.target == "B",
            A_RESERVE_READY=None, DUAL_RESERVE_READY=False, SECOND_FAULT_QUALIFIED=False,
            scope="UNIT_SEQUENCE_NOT_STORAGE_DYNAMICS_NOT_PLC_RECEIPT")
        self.history.append(row); return row
