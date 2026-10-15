"""FINAL aggregation DEVELOPMENT replay from immutable archived inputs.

This is not formal admission, a new candidate execution, or a qualification gate.
"""
import ast
import hashlib
import json
import os
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

from v0_2.tests.tools.m1_c3c_v4.authority import require, load_bound
from v0_2.tests.tools.m1_c3c_v4.runtime_admission import ROOT
from v0_2.tests.tools.m1_c3c_v5_readback.readback import readback


def verify_wrapper_derivation():
    """Output destination is the only aggregate-helper AST difference."""
    def normalized(path, function_name):
        tree = ast.parse(path.read_bytes())
        f = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == function_name)
        f.name = "normalized_aggregate"
        f.args.args = [a for a in f.args.args if a.arg != "output_root"]
        writes = []
        for n in ast.walk(f):
            if isinstance(n, ast.ImportFrom) and len(n.names) == 1 and n.names[0].name == "verify":
                n.module, n.level = "v0_2.tests.tools.m1_engine_v3.evidence", 0
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "write":
                writes.append(ast.dump(n.args[1], include_attributes=False))
                n.args[0] = ast.Constant(value="ONLY_OUTPUT_DESTINATION_DIFFERS")
        return ast.dump(f, include_attributes=False), writes
    target = Path(__file__).with_name("derived.py")
    for source, old, new, count in (
        ("startup_execution.py", "aggregate", "aggregate_startup", 2),
        ("witness_matrix.py", "collect", "collect_witnesses", 1)):
        left = normalized(ROOT / "v0_2/tests/tools/m1_engine_v3" / source, old)
        right = normalized(target, new)
        require(left == right and len(left[1]) == count, "AGGREGATE_HELPER_SEMANTIC_DERIVATION_DRIFT")


def replay(control, folder, mark):
    timings = {}
    @contextmanager
    def phase(name):
        started = time.perf_counter()
        mark("AGGREGATE_PHASE_BEGIN", phase=name)
        try:
            yield
        except Exception as error:
            mark("AGGREGATE_PHASE_FAIL", phase=name, error_type=type(error).__name__,
                 error=str(error), wall_s=time.perf_counter() - started)
            raise
        finally:
            timings[name] = time.perf_counter() - started
        mark("AGGREGATE_PHASE_END", phase=name, wall_s=timings[name])

    with phase("NATIVE_ARCHIVE_READBACK"):
        native = readback(control, folder, mark)
    archive_path = ROOT / control["archive"]["local_path"]
    extraction = control["aggregate_inputs"]
    prefix = extraction["archive_prefix"]
    input_root = ROOT / "artifacts" / prefix.rstrip("/")
    derived_root = ROOT / "artifacts/m1-autonomous-development" / (
        "v5-aggregate-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"])
    require(not input_root.exists() and not derived_root.exists(), "ARCHIVE_REPLAY_MUST_START_CLEAN")
    require(input_root.is_relative_to(ROOT / "artifacts/m1-autonomous-development"),
            "ARCHIVE_REPLAY_INPUT_SCOPE")
    manifest_path = folder / "materialized_input_hashes.jsonl"
    with phase("MATERIALIZE_EXACT_INPUT_BYTES"):
        total = 0
        with zipfile.ZipFile(archive_path) as archive, manifest_path.open("xb") as manifest:
            selected = [e for e in archive.infolist() if e.filename.startswith(prefix)]
            require(len(selected) == extraction["file_count"], "AGGREGATE_INPUT_FILE_COUNT")
            for index, entry in enumerate(selected):
                target = ROOT / "artifacts" / entry.filename
                require(target.resolve().is_relative_to(input_root.resolve()),
                        "AGGREGATE_INPUT_PATH_ESCAPE")
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                size = 0
                with archive.open(entry) as source, target.open("xb") as output:
                    while chunk := source.read(65536):
                        output.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                require(size == entry.file_size, "AGGREGATE_INPUT_COPY_TRUNCATED")
                total += size
                manifest.write(json.dumps({"path": entry.filename, "bytes": size,
                    "raw_sha256": digest.hexdigest()}, sort_keys=True).encode() + b"\n")
                if (index + 1) % 1000 == 0:
                    manifest.flush()
                    os.fsync(manifest.fileno())
                    mark("AGGREGATE_INPUT_COPY_PROGRESS", files=index + 1, bytes=total)
            manifest.flush()
            os.fsync(manifest.fileno())
        require(total == extraction["bytes"], "AGGREGATE_INPUT_BYTE_COUNT")

    # Read-only helpers can import model class definitions. No replay(), update(),
    # SplitEngine constructor or controlled plant call is performed by this module.
    from v0_2.tests.tools.m1_engine_v3.common import read
    from v0_2.tests.tools.m1_engine_v3.evidence import write, receipt, verify
    from v0_2.tests.tools.m1_engine_v3.final_validation import groups
    from v0_2.tests.tools.m1_engine_v3.eligibility import evaluate
    from v0_2.tests.tools.m1_engine_v3.artifact_schemas import validate_run
    from v0_2.tests.tools.m1_c3c_v4.final_gate import validate_sem02, validate_pf06
    from .derived import aggregate_startup, collect_witnesses
    with phase("FROZEN_HELPER_DERIVATION_CHECK"):
        verify_wrapper_derivation()
    descriptors = read("phase5_r5_2_1r4_7_c3_a_reference_oracle_spec.json")["input_inventory"]
    require(len(descriptors) == 101 and sum(d["row_count"] for d in descriptors) == 3216,
            "AGGREGATE_DESCRIPTOR_IDENTITY")
    cases = input_root / "cases"
    stages, prefixes = {}, {}
    with phase("CASE_PREFIX_REPEAT_METADATA"):
        for i in range(101):
            directory = cases / ("%03d" % i)
            stage = verify(receipt(directory / "stage_result.json"))
            require(stage["status"] == "PASS" and stage["repeat_pass"]
                    and stage["comparison"]["status"] == "PASS", "C3C_CASE_NOT_VALID_PASS")
            require(verify(receipt(directory / "schema_readback.json"))["status"] == "PASS",
                    "C3C_CASE_SCHEMA_NOT_PASS")
            stages[i] = {**stage, "stage_receipt": receipt(directory / "stage_result.json")}
            prefixes[i] = verify(receipt(directory / "prefix_result.json"))
            require(prefixes[i]["status"] == "PASS", "C3C_SELECTED_PREFIX_INCOMPLETE")
            mark("AGGREGATE_CASE_METADATA_CHECKED", index=i)
    with phase("HISTORY_GROUPS_REFERENCE"):
        reference_groups = groups(cases, reference=True)
    with phase("HISTORY_GROUPS_SPLIT"):
        split_groups = groups(cases)
    with phase("ORIGINAL_STARTUP_AND_VERSIONED_COMPATIBILITY"):
        startup = aggregate_startup(input_root / "startup", input_root / "startup_inventory.json",
                                    cases, derived_root / "startup")
    with phase("PF_WITNESS_MATRIX"):
        matrix = collect_witnesses(input_root, descriptors, stages, derived_root)
    with phase("SEM02_CAUSAL_ELIGIBILITY"):
        eligibility = evaluate(startup)
        write(derived_root / "startup_eligibility.json", eligibility)
        write(derived_root / "PF16_witness_matrix.json", matrix)
    with phase("SOURCE_CASE_ARTIFACT_SCHEMAS"):
        source_schema = validate_run(input_root)
    with phase("DERIVED_ARTIFACT_SCHEMAS"):
        derived_schema = validate_run(derived_root)
    definition = json.loads((ROOT / control["reference_package_path"]).read_bytes())
    def registration(name):
        path = definition["registration_paths"][name]
        return load_bound((ROOT / path).read_bytes(), definition["registration_raw_sha256"][name])
    with phase("REGISTERED_SEM02_AND_PF06_COMPARISON"):
        validate_sem02(eligibility, registration("SEM02"))
        validate_pf06(matrix, registration("PF06_supplement"))
        require(startup["historical_guard"]["ORIGINAL_STARTUP_HISTORICAL_RESULT"] == "49/50"
                and startup["versioned_compatibility"] == "PASS", "C3C_STARTUP_NOT_EXACT")
    with phase("VERIFY_INPUTS_REMAIN_BYTE_IDENTICAL"):
        count = 0
        with manifest_path.open("rb") as stream:
            for line in stream:
                row = json.loads(line)
                path = ROOT / "artifacts" / row["path"]
                h = hashlib.sha256()
                with path.open("rb") as source:
                    while chunk := source.read(65536):
                        h.update(chunk)
                require(path.stat().st_size == row["bytes"] and h.hexdigest() == row["raw_sha256"],
                        "ARCHIVED_INPUT_MUTATED_BY_AGGREGATION")
                count += 1
                if count % 1000 == 0:
                    mark("AGGREGATE_INPUT_POSTCHECK_PROGRESS", files=count)
        require(count == extraction["file_count"], "AGGREGATE_INPUT_POSTCHECK_COUNT")
    return {"scope": "ARCHIVED_FINAL_AGGREGATION_DEVELOPMENT_REPLAY",
        "source_formal_run": control["archive"]["run_id"], "source_formal_gate": "INVALID_C3_C_EXECUTION",
        "native_archive_readback": native, "case_count": len(stages),
        "selected_prefix_count": sum(x["selected_count"] for x in prefixes.values()),
        "snapshot_count": sum(x["required_snapshot_count"] for x in stages.values()),
        "original_startup_historical": "49/50", "versioned_startup_compatibility": startup["versioned_compatibility"],
        "reference_groups": reference_groups, "split_groups": split_groups,
        "sem02_excluded_cases": eligibility["nonqualified_case_count"],
        "strict_P1_Lane_B_C": "INCOMPLETE", "PF06_original_scope": "INCOMPLETE",
        "PF06_supplemental_scope": matrix["PF06_proposal"]["PF06_SUPPLEMENTAL_SOURCE"],
        "source_schema": source_schema, "derived_schema": derived_schema, "phase_wall_s": timings,
        "original_inputs_byte_identical_after": True, "new_formal_execution": False,
        "candidate_behavioral_execution": False, "formal_qualification": False,
        "new_fresh_campaign": False, "qualified_result_generated": False}
