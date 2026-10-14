"""Full registered input use through the unchanged installed SDK CLI."""
import contextlib
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def write_raw(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise OSError("SDK_EVIDENCE_READBACK_FAILURE")
    return {"name": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    return write_raw(path, json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode() + b"\n")


def main():
    _, directory, expected_control = sys.argv[1:]
    directory = Path(directory).resolve()
    if (platform.node().upper() == "HIPPO" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Windows"
            or not directory.is_relative_to(ROOT / "artifacts/m1-sdk-extended")):
        raise ValueError("EXTENDED_INSTALL_HOST_SCOPE_DENIED")
    write(directory / "ready.json", {"pid": os.getpid(), "executable": sys.executable})
    deadline = time.monotonic() + 25
    while not (directory / "release.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("EXTENDED_INSTALL_JOB_RELEASE_TIMEOUT")
        time.sleep(0.05)
    if json.loads((directory / "release.json").read_bytes())["actual_python_pid"] != os.getpid():
        raise ValueError("EXTENDED_INSTALL_PID_RELEASE_MISMATCH")
    control = ROOT / "v0_2/tests/tools/m1_release_v2/delivery_control.json"
    if hashlib.sha256(control.read_bytes()).hexdigest() != expected_control:
        raise ValueError("EXTENDED_CONTROL_IDENTITY")
    definition = json.loads(control.read_bytes())
    for name, digest in definition["source_hashes"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("EXTENDED_SOURCE_DRIFT: " + name)
    lock = json.loads((ROOT / "v0_2/tests/tools/c3b_v14_1/development_environment_lock_v1.json").read_bytes())
    dependencies = {name: importlib.metadata.version(name) for name in lock["dependencies"]}
    if platform.python_version() != "3.11.9" or dependencies != lock["dependencies"]:
        raise ValueError("EXTENDED_VENV_DEPENDENCY_DRIFT")
    sdk = Path(os.environ["C2C_SDK_ROOT"]).resolve()
    workspace = Path(os.environ["C2C_SDK_WORKSPACE"]).resolve()
    archive = Path(os.environ["C2C_SDK_ZIP"]).resolve()
    if sdk.is_relative_to(ROOT) or workspace.is_relative_to(ROOT) or sdk == workspace:
        raise ValueError("EXTENDED_REQUIRES_OUTSIDE_CHECKOUT")
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_sha != definition["sdk_zip_sha256"]:
        raise ValueError("ORIGINAL_INSTALLED_SDK_ZIP_DRIFT")
    delivery = json.loads((sdk / "DELIVERY_MANIFEST.json").read_bytes())
    if delivery["source_commit"] != definition["sdk_source_commit"]:
        raise ValueError("ORIGINAL_SDK_SOURCE_IDENTITY")
    def verify_package():
        for entry in delivery["files"]:
            p = (sdk / entry["path"]).resolve()
            if (not p.is_relative_to(sdk) or p.stat().st_size != entry["bytes"]
                    or hashlib.sha256(p.read_bytes()).hexdigest() != entry["sha256"]):
                raise ValueError("EXTENDED_SDK_BYTE_DRIFT")
    verify_package()
    spec_raw = (sdk / "phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json").read_bytes()
    if hashlib.sha256(spec_raw).hexdigest() != definition["input_spec_sha256"]:
        raise ValueError("INSTALLED_INPUT_SPEC_DRIFT")
    inventory = json.loads(spec_raw)["input_inventory"]
    expected = [{"index": i, "row_count": d["row_count"],
                 "input_canonical_sha256": d["input_canonical_sha256"]}
                for i, d in enumerate(inventory)]
    if expected != definition["cases"] or len(expected) != 101:
        raise ValueError("EXTENDED_CASE_INVENTORY_DRIFT")
    os.chdir(workspace)
    sys.path[:] = [p for p in sys.path if p and not Path(p).resolve().is_relative_to(ROOT)]
    for name in list(sys.modules):
        if name == "v0_2" or name.startswith("v0_2."):
            del sys.modules[name]
    importlib.invalidate_caches()
    results = []
    started = time.monotonic()
    with (directory / "events.jsonl").open("xb") as events:
        def event(kind, **fields):
            value = {"event": kind, "elapsed_s": time.monotonic() - started, **fields}
            events.write(json.dumps(value, sort_keys=True).encode() + b"\n")
            events.flush()
            os.fsync(events.fileno())
            print(json.dumps(value, sort_keys=True), flush=True)
        def invoke(arguments, name):
            stream = io.StringIO()
            sys.argv = [str(sdk / "sdk_cli.py"), *arguments]
            with contextlib.redirect_stdout(stream):
                runpy.run_path(str(sdk / "sdk_cli.py"), run_name="__main__")
            raw = stream.getvalue().encode()
            receipt = write_raw(directory / name, raw)
            return json.loads(raw), receipt
        try:
            event("DESCRIBE_BEGIN")
            description, describe_receipt = invoke(["--describe", "--verify"], "describe.raw.json")
            event("DESCRIBE_END", verified_files=description["verified_files"])
            for case in expected:
                i, n = case["index"], case["row_count"]
                event("CASE_BEGIN", index=i, rows=n, input_sha256=case["input_canonical_sha256"])
                output, receipt = invoke(["--run", "--input-index", str(i), "--rows", str(n)],
                                         "case-%03d.raw.json" % i)
                source = Path(sys.modules["v0_2.tests.tools.m1_engine_v4.engine"].__file__).resolve()
                if (not source.is_relative_to(sdk) or output["comparison"]["status"] != "PASS"
                        or output["comparison"]["compared_rows"] != n
                        or output["example_prefix_rows"] != n
                        or output["source_commit"] != definition["sdk_source_commit"]
                        or output["sut"] != "v0_2.tests.tools.m1_engine_v4.engine.SplitEngine"):
                    raise ValueError("INSTALLED_FULL_INPUT_ASSERTION_FAIL: " + str(i))
                results.append({**case, "status": "PASS", "final_state": output["final_state"],
                                "output_receipt": receipt, "imported_sut_file": str(source)})
                event("CASE_END", index=i, rows=n, result="PASS", output_sha256=receipt["sha256"])
        except BaseException as error:
            event("STOP", error_type=type(error).__name__, error=str(error), completed=len(results))
            write(directory / "failure.json", {"status": "STOP", "completed_cases": results,
                  "error_type": type(error).__name__, "error": str(error), "same_execution_retry": False})
            raise
    verify_package()
    after = {name: importlib.metadata.version(name) for name in lock["dependencies"]}
    if dependencies != after or len(results) != 101:
        raise ValueError("EXTENDED_INSTALL_ENV_OR_COVERAGE_DRIFT")
    write(directory / "result.json", {"status": "SDK_OUTSIDE_CHECKOUT_ALL_INPUTS_PASS",
          "source_commit": os.environ["GITHUB_SHA"], "sdk_source_commit": delivery["source_commit"],
          "control_manifest_sha256": expected_control, "archive_sha256": archive_sha,
          "venv_python": sys.executable, "dependencies": dependencies,
          "working_directory": str(workspace), "describe_receipt": describe_receipt,
          "cases": results, "case_count": 101, "rows": sum(c["row_count"] for c in expected),
          "elapsed_s": time.monotonic() - started, "full_campaign_credit": False,
          "formal_qualification": False, "production": False, "hardware": "CALIBRATION_REQUIRED"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
