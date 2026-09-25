"""Phase 5.1R plant-only scan and frozen-baseline qualification runner."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from math import fsum
from pathlib import Path

from v0_2.plant.authority import traces_for_run
from v0_2.plant.fixtures import physical_fixture
from v0_2.plant.phase4_harness import run
from v0_2.thermal.provenance import fixture_parameter as p

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = ROOT / "phase5_1r_qualification_registration.json"
SCAN_OUT = ROOT / "docs/results/phase5_1r_feasibility_scan.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controls(base, speed: float):
    return replace(base, speed_actual=p("phase5_1r.fixed_speed", speed, "fraction"))


def _window_mean_max_device(rows, start_ns: int) -> float:
    by_time = defaultdict(list)
    for row in rows:
        if row.time_ns >= start_ns:
            by_time[row.time_ns].append(row.device_temperature_k)
    maxima = [max(values) for _, values in sorted(by_time.items())]
    return fsum(maxima) / len(maxima)


def plant_only_scan() -> dict[str, object]:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    rule = registration["plant_only_feasibility_rule"]
    results = []
    for load in registration["candidate_grid_w_per_device"]:
        plant, base = physical_fixture(branch_count=2, power_each=load)
        endpoints = {}
        for label, speed in (
            ("low", rule["low_cooling_speed_fraction"]),
            ("maximum", rule["maximum_qualified_cooling_speed_fraction"]),
        ):
            result = run(
                plant,
                _controls(base, speed),
                rule["duration_ns"],
                registration["dt_meshes_ns"][0],
            )
            rows = traces_for_run(result)
            metrics = result.metrics()
            endpoints[label] = {
                "speed_fraction": speed,
                "qualified_window_mean_max_device_k": _window_mean_max_device(
                    rows, rule["qualified_window_start_ns"]
                ),
                "final_max_device_k": max(
                    row.device_temperature_k
                    for row in rows
                    if row.time_ns == max(x.time_ns for x in rows)
                ),
                "max_mass_residual_kg_s": max(
                    metrics["max_mass_node_residual_kg_s"],
                    metrics["max_mass_volume_residual_kg_s"],
                ),
                "max_energy_residual_j": max(
                    abs(step.ledger.full_loop_residual_j) for step in result.accepted
                ),
            }
        bracketed = (
            endpoints["low"]["qualified_window_mean_max_device_k"] > 305.5
            and endpoints["maximum"]["qualified_window_mean_max_device_k"] < 304.5
        )
        results.append(
            {
                "candidate_id": f"LOAD-{int(load):03d}",
                "power_w_per_device": load,
                "low_cooling": endpoints["low"],
                "maximum_cooling": endpoints["maximum"],
                "target_bracketed_by_plant": bracketed,
            }
        )
    feasible = [x for x in results if x["target_bracketed_by_plant"]]
    selected = max(feasible, key=lambda x: x["power_w_per_device"]) if feasible else None
    return {
        "schema": "phase5-1r-plant-only-feasibility-v1",
        "qualification_registration_sha256": _sha(REGISTRATION),
        "controller_executed": False,
        "selection_uses_closed_loop_metrics": False,
        "candidates": results,
        "selected": (
            {
                "scenario_id": "NOMINAL-FEASIBLE-01",
                "candidate_id": selected["candidate_id"],
                "power_w_per_device": selected["power_w_per_device"],
            }
            if selected is not None
            else None
        ),
        "status": "PASS" if selected is not None else "NO_FEASIBLE_REGULATION_REGION",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-only", action="store_true")
    args = parser.parse_args()
    result = plant_only_scan()
    SCAN_OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not args.scan_only:
        raise SystemExit("Closed-loop qualification runner not invoked; use the frozen scan result first")


if __name__ == "__main__":
    main()
