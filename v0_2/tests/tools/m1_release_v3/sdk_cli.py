"""Offline SDK entry using the existing bounded complete-trace storage backend."""
import argparse
import hashlib
import json
import platform
import sys
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="C2C-DTB offline streaming SDK; no hardware control")
    parser.add_argument("--verify", action="store_true", help="verify payload hashes; external ZIP SHA is still required")
    parser.add_argument("--describe", action="store_true", help="show frozen parameters without running models")
    parser.add_argument("--run", action="store_true", help="explicitly run an offline registered input prefix")
    parser.add_argument("--input-index", type=int, default=15, help="registered index0..100")
    parser.add_argument("--rows", type=int, default=3, help="positive prefix length in the registered domain")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "DELIVERY_MANIFEST.json").read_bytes())
    for entry in manifest["files"]:
        path = (root / entry["path"]).resolve()
        if (not path.is_relative_to(root) or path.stat().st_size != entry["bytes"]
                or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]):
            raise ValueError("DELIVERY_FILE_DRIFT: " + entry["path"])
    output = {"scope": "OFFLINE_DEVELOPMENT_SDK_NOT_FORMAL_QUALIFICATION",
              "verified_files": len(manifest["files"]), "source_commit": manifest["source_commit"],
              "hardware": "CALIBRATION_REQUIRED", "sdk_storage": "COMPLETE_STREAMED_TRACES_AND_IMMUTABLE_JOURNAL"}
    if args.describe or not args.run:
        output["parameters"] = json.loads((root / "phase5_r5_2_2_fixture_tracking_profile.json").read_bytes())
    if args.run:
        if platform.node().upper() == "HIPPO":
            raise ValueError("MODEL_EXECUTION_DISABLED_ON_KNOWN_HARD_HANG_HOST")
        sys.path.insert(0, str(root))
        from v0_2.tests.tools.m1_engine_v3.common import read, guard
        from v0_2.tests.tools.m1_engine_v3.materializer import extract
        from v0_2.tests.tools.m1_engine_v3.replay_stream import write_reference, write_split
        from v0_2.tests.tools.m1_engine_v3.stream_trace import TraceReader, OracleBridge
        from v0_2.tests.tools.m1_engine_v3.oracle import OracleTrace
        from v0_2.tests.tools.m1_engine_v3.comparator import compare_traces
        from v0_2.tests.tools.m1_engine_v4.integration_bindings import sut_bindings
        from v0_2.tests.tools.m1_remote_control_v3.progress import initialize, close
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
        # UUID is storage identity only; no random fixture/model input is introduced.
        directory = root / "artifacts/m1-autonomous-development" / ("sdk-" + uuid.uuid4().hex)
        directory.mkdir(parents=True, exist_ok=False)
        initialize(directory / "progress.jsonl", stage_id="SDK_FULL_INPUT", sut_version="v4")
        try:
            write_reference(rows, profile, classifier, directory / "reference.json",
                            replay_kind=descriptor["replay_kind"])
            with sut_bindings() as constructors:
                write_split(rows, profile, classifier, directory / "split.json",
                            case=descriptor["replay_kind"])
            if (len(constructors) != 1 or constructors[0]["class"] != "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine"
                    or constructors[0]["post_module"] != "v0_2.tests.tools.m1_engine_v4.engine"):
                raise ValueError("SDK_STREAM_WRONG_SUT")
            reference = TraceReader(directory / "reference.json")
            split = TraceReader(directory / "split.json")
            reference.verify_all()
            split.verify_all()
            oracle = OracleBridge(OracleTrace("source-" + str(args.input_index), full_rows), reference)
            comparison = compare_traces(reference, split, oracle=oracle)
            if comparison["status"] != "PASS":
                raise ValueError("SDK_PREFIX_DEVELOPMENT_COMPARISON_FAIL: " + str(comparison))
            output.update(example_prefix_rows=len(rows), comparison=comparison,
                          sut=constructors[0]["class"], final_state=split[-1]["POST"]["state"],
                          prefix_example_is_not_full_campaign=True,
                          complete_trace_directory=str(directory),
                          complete_reference_trace_sha256=reference.index["document_receipt"]["raw_sha256"],
                          complete_split_trace_sha256=split.index["document_receipt"]["raw_sha256"])
        finally:
            close()
    print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
