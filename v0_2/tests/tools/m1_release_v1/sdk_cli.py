"""Read-only parameter inspection and explicitly requested offline prefix example."""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="C2C-DTB offline V4 source SDK; no hardware control")
    parser.add_argument("--verify", action="store_true", help="verify listed files; also check the trusted external ZIP SHA")
    parser.add_argument("--describe", action="store_true", help="show frozen fixture parameters and provenance")
    parser.add_argument("--run", action="store_true", help="explicitly run a small offline input prefix")
    parser.add_argument("--input-index", type=int, default=15, help="registered descriptor index0..100")
    parser.add_argument("--rows", type=int, default=3, help="positive prefix length within this descriptor")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "DELIVERY_MANIFEST.json").read_bytes())
    for entry in manifest["files"]:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("DELIVERY_PATH_ESCAPE")
        raw = path.read_bytes()
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("DELIVERY_FILE_DRIFT: " + entry["path"])
    output = {"scope": "OFFLINE_DEVELOPMENT_SDK_NOT_FORMAL_QUALIFICATION", "verified_files": len(manifest["files"]),
              "source_commit": manifest["source_commit"], "hardware": "CALIBRATION_REQUIRED"}
    if args.describe or not args.run:
        output["parameters"] = json.loads((root / "phase5_r5_2_2_fixture_tracking_profile.json").read_bytes())
    if args.run:
        if platform.node().upper() == "HIPPO":
            raise ValueError("MODEL_EXECUTION_DISABLED_ON_KNOWN_HARD_HANG_HOST")
        sys.path.insert(0, str(root))
        from v0_2.tests.tools.m1_engine_v3.common import read, guard
        from v0_2.tests.tools.m1_engine_v3.materializer import extract
        from v0_2.tests.tools.m1_engine_v3.scheduler import SimulatedPLC, MeasurementView
        from v0_2.tests.tools.m1_engine_v3.observer import reference_rows
        from v0_2.tests.tools.m1_engine_v3.oracle import OracleTrace
        from v0_2.tests.tools.m1_engine_v3.comparator import compare_traces
        from v0_2.tests.tools.m1_engine_v4.engine import SplitEngine
        guard()
        inventory = read("phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json")["input_inventory"]
        if not 0 <= args.input_index < len(inventory):
            raise ValueError("UNREGISTERED_DESCRIPTOR_INDEX")
        descriptor = inventory[args.input_index]
        full_rows = extract(descriptor)["observations"]
        if not 0 < args.rows <= len(full_rows):
            raise ValueError("PREFIX_OUT_OF_INPUT_DOMAIN")
        rows = full_rows[:args.rows]
        profile = read("phase5_r5_2_2_fixture_tracking_profile.json")
        classifier = read("phase5_r5_2_silent_tracking_fault_registration.json")["classifier"]
        reference = reference_rows(rows, profile, classifier, replay_kind=descriptor["replay_kind"])
        engine, plc = SplitEngine(profile, classifier), SimulatedPLC(rows)
        frames = []
        for i, row in enumerate(rows):
            provenance = "POST_COMMAND_EFFECT" if descriptor["replay_kind"] == "ST-08" and row["time_ns"] == 600000000 else "CERTIFIED_INTERVAL_END"
            measurement = MeasurementView.from_row(row, provenance)
            pre = engine.pre(measurement, plc.prior, "sdk:" + str(i))
            engine.accept_plc(plc.issue(engine.safety(pre), measurement))
            frames.append(engine.post())
        oracle = OracleTrace("source-" + str(args.input_index), full_rows)
        comparison = compare_traces(reference["frames"], frames, oracle=oracle)
        if comparison["status"] != "PASS":
            raise ValueError("SDK_PREFIX_DEVELOPMENT_COMPARISON_FAIL: " + str(comparison))
        output.update(example_prefix_rows=len(rows), comparison=comparison,
                      sut=type(engine).__module__ + "." + type(engine).__name__,
                      final_state=frames[-1]["POST"]["state"],
                      prefix_example_is_not_full_campaign=True)
    print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
