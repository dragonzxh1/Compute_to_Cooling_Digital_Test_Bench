"""Read-only historical archive audit, NOT a new formal execution.

Versioned copy of the tested invariant-hoisted auditor. Only artifact access and
explicit source-run context differ. No process environment is changed or forged.
"""
import json
from pathlib import Path
from v0_2.tests.tools.m1_c3c_v4.authority import (
    SCOPE, digest, load_bound, require, verify_environment)
from v0_2.tests.tools.m1_c3c_v4.runtime_admission import ROOT, package


class ArchivePath:
    def __init__(self, root, name):
        self.root, self.name = root, name

    def read_bytes(self):
        require(self.name in self.root.names, "READBACK_MISSING_ENTRY: " + self.name)
        return self.root.archive.read(self.name)

    @property
    def parent(self):
        return ArchivePath(self.root, self.name.rsplit("/", 1)[0])

    def __truediv__(self, child):
        require(type(child) is str and "/" not in child and "\\" not in child
                and child not in ("", ".", ".."), "READBACK_CHILD_PATH_ESCAPE")
        return ArchivePath(self.root, self.name + "/" + child)

    def __str__(self):
        return "official.zip!/" + self.name


class ArchiveRoot:
    def __init__(self, archive, names, prefix, quarantine):
        self.archive, self.names = archive, names
        self.prefix, self.quarantine = prefix, quarantine

    def rglob(self, basename):
        # The quarantined FINAL subtree is separately checked as FAILED, never
        # silently interpreted as a successful batch or omitted from the verdict.
        return [ArchivePath(self, n) for n in self.names
                if n.startswith(self.prefix) and n.rsplit("/", 1)[-1] == basename
                and not n.startswith(self.quarantine)]

def archive_audit(archive_root, identity, *, source_run_id, source_run_attempt, progress=None):
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "v0_2/tests/tools/m1_c3c_v4/artifact_schema.json").read_bytes())
    validator = Draft202012Validator(schema)
    native_root = archive_root
    batches = list(native_root.rglob("batch_complete.json"))
    require(bool(batches) and not list(native_root.rglob("batch_stop.json")), "C3C_BATCH_INCOMPLETE_OR_STOPPED")
    # The admitted, immutable definition is invocation-local, never a global cache.
    # Existing source-byte guards still run before and after the parent stage.
    _, definition = package()
    lock_name = definition["execution"]["environment_lock"]
    expected = load_bound((ROOT / lock_name).read_bytes(), definition["source_raw_sha256"][lock_name])
    stage_ids = []; captures = 0; constructors = 0
    for path in batches:
        batch = json.loads(path.read_bytes())
        require(batch["status"] == "COMPLETE" and batch["scope"] == SCOPE
                and batch["execution_identity"] == identity and batch["formal_execution_authorized"] is True,
                "C3C_BATCH_AUTHORITY_MISMATCH")
        for i, stage in enumerate(batch["stages"]):
            require(stage["status"] == "PASS", "C3C_NONPASS_STAGE_IN_BATCH")
            outer_path = path.parent / ("stage-%03d-result.json" % i)
            require(digest(outer_path.read_bytes()) == batch["receipts"][i]["result_raw_sha256"], "C3C_STAGE_RECEIPT_DRIFT")
            folder = path.parent / stage["stage_id"]
            native = json.loads((folder / "job_status.json").read_bytes())
            start = json.loads((folder / "job_start.json").read_bytes())
            proof = json.loads((folder / "external_job_identity.json").read_bytes())
            ready = json.loads((folder / "ready.json").read_bytes())
            release = json.loads((folder / "release.json").read_bytes())
            require(native["outcome"] == "EXITED" and native["child_exitcode"] == 0
                    and native["cleanup_complete"] and native["active_after_cleanup"] == 0
                    and native["assigned_before_resume"] and native["resumed"]
                    and native["pid"] == start["pid"] and proof["in_target_job"]
                    and proof["actual_python_pid"] == ready["pid"] == release["actual_python_pid"]
                    and proof["target_job_name"] == start["job_name"], "C3C_ACTUAL_PYTHON_JOB_OR_CLEANUP")
            require(proof["cpu_rate"] == 2500 and proof["cpu_flags"] == 5 and proof["max_active_processes"] == 4
                    and proof["process_mb"] == 1024 and proof["job_mb"] == 2048
                    and start["wall_ms"] == 480000 and start["kill_on_close"], "C3C_RESOURCE_POLICY_DRIFT")
            require(release["external_proof_raw_sha256"] == digest((folder / "external_job_identity.json").read_bytes()),
                    "C3C_RELEASE_PROOF_DRIFT")
            raw = json.loads((folder / "raw_evidence_receipts.json").read_bytes())
            require(set(raw) == {"stdout.raw", "stderr.raw", "verify_stdout.raw", "verify_stderr.raw"}, "C3C_RAW_LOG_SET")
            for name, receipt in raw.items():
                require(receipt["status"] == "PERSISTED" and digest((folder / name).read_bytes()) == receipt["raw_sha256"], "C3C_RAW_LOG_HASH")
                captures += 1
            result = json.loads((folder / "result.json").read_bytes())
            validator.validate(result)
            require(result["status"] == "PASS" and result["execution_identity"] == identity
                    and result["github_run_id"] == source_run_id
                    and result["github_run_attempt"] == source_run_attempt, "C3C_FRESH_STAGE_IDENTITY")
            require(result["runtime_identity_before"] == result["runtime_identity_after"], "C3C_STAGE_ENVIRONMENT_DRIFT")
            verify_environment(result["runtime_identity_before"], expected)
            constructors += len(result["sut_constructors"])
            stage_ids.append(stage["stage_id"])
        if progress is not None:
            progress(completed_stage_records=len(stage_ids), batch=str(path))
    # The FINAL stage's own batch is not complete until this function returns.
    # Its before/after source/Job/raw evidence is independently checked by the
    # parent and mandatory delivery readback, not fictitiously pre-counted here.
    return {"status": "HISTORICAL_NATIVE_READBACK_COMPLETE", "completed_batches": len(batches), "completed_stages": len(stage_ids),
            "raw_captures": captures, "actual_sut_constructors": constructors,
            "stage_ids": stage_ids, "final_current_batch_post_audit_required": True}

