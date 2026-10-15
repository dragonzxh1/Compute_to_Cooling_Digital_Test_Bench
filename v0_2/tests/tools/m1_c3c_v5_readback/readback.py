"""Bound historical evidence readback only. Never promotes an INVALID run."""
import hashlib
import json
import os
import stat
import time
import zipfile
from pathlib import Path, PurePosixPath

from v0_2.tests.tools.m1_c3c_v4.authority import require
from v0_2.tests.tools.m1_c3c_v4.runtime_admission import ROOT
from .audit import ArchiveRoot, archive_audit


def readback(control, folder, mark):
    source = control["archive"]
    path = (ROOT / source["local_path"]).resolve()
    require(path.is_relative_to(ROOT / "artifacts/m1-c3c-v5-readback-input"),
            "ARCHIVE_INPUT_PATH_ESCAPE")
    require(path.stat().st_size == source["bytes"], "OFFICIAL_ARCHIVE_SIZE_DRIFT")
    started = time.perf_counter()
    mark("OFFICIAL_ARCHIVE_DIGEST_BEGIN", bytes=source["bytes"])
    hasher = hashlib.sha256()
    processed = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
            processed += len(chunk)
            if processed % (256 * 1024 * 1024) == 0:
                mark("OFFICIAL_ARCHIVE_DIGEST_PROGRESS", bytes=processed)
    require(hasher.hexdigest() == source["raw_sha256"], "OFFICIAL_ARCHIVE_DIGEST_DRIFT")
    digest_wall = time.perf_counter() - started
    mark("OFFICIAL_ARCHIVE_DIGEST_COMPLETE", wall_s=digest_wall)
    with zipfile.ZipFile(path) as archive:
        names = {}
        lower_names = set()
        for item in archive.infolist():
            name = item.filename
            parsed = PurePosixPath(name)
            require(not item.is_dir() and name == parsed.as_posix()
                    and not parsed.is_absolute() and ":" not in name and "\\" not in name
                    and not any(x in (".", "..") for x in parsed.parts),
                    "OFFICIAL_ARCHIVE_PATH_ESCAPE")
            require(name not in names and name.casefold() not in lower_names,
                    "OFFICIAL_ARCHIVE_DUPLICATE_ENTRY")
            require(not stat.S_ISLNK(item.external_attr >> 16), "OFFICIAL_ARCHIVE_SYMLINK")
            names[name] = item
            lower_names.add(name.casefold())
        require(len(names) == source["entry_count"], "OFFICIAL_ENTRY_COUNT_DRIFT")
        prefix = source["native_prefix"]
        quarantine = prefix + "final/"
        quarantined = [n for n in names if n.startswith(quarantine)]
        require(len(quarantined) == source["quarantined_final_entry_count"],
                "FAILED_FINAL_QUARANTINE_COUNT_DRIFT")
        for suffix, expected in source["failed_final_required_raw_sha256"].items():
            require(hashlib.sha256(archive.read(quarantine + suffix)).hexdigest() == expected,
                    "FAILED_FINAL_EVIDENCE_DRIFT")
        stop = json.loads(archive.read(quarantine + "batch_stop.json"))
        failed = json.loads(archive.read(quarantine + "FINAL_ACCEPTANCE/job_status.json"))
        require(stop["status"] == "STOPPED_NOT_FULL_PASS" and failed["outcome"] == "TIMEOUT"
                and failed["cleanup_complete"] and failed["active_after_cleanup"] == 0,
                "ARCHIVED_FAILED_FINAL_STATE_NOT_PRESERVED")
        mark("FAILED_FINAL_QUARANTINED_AS_INVALID", entries=len(quarantined))
        native_root = ArchiveRoot(archive, names, prefix, quarantine)
        audit_start = time.perf_counter()
        mark("NATIVE_AUDIT_BEGIN", expected_records=source["upstream_stage_records"])
        audit = archive_audit(native_root, source["execution_identity"],
            source_run_id=str(source["run_id"]), source_run_attempt=str(source["run_attempt"]),
            progress=lambda **values: mark("NATIVE_BATCH_COMPLETE", **values))
        audit_wall = time.perf_counter() - audit_start
        require(audit["completed_batches"] == source["upstream_complete_batches"]
                and audit["completed_stages"] == source["upstream_stage_records"]
                and audit["raw_captures"] == source["upstream_raw_captures"],
                "ARCHIVED_NATIVE_COVERAGE_DRIFT")
        spec = json.loads((ROOT / control["reference_package_path"]).read_bytes())
        scope = spec["registration_paths"]["limited_scope"]
        required = json.loads((ROOT / scope).read_bytes())["required_static_stage_ids"]
        require(len(required) == 969 and set(required).issubset(set(audit["stage_ids"])),
                "ARCHIVED_STATIC_STAGE_COVERAGE_MISSING")
        mark("NATIVE_AUDIT_COMPLETE", wall_s=audit_wall,
             records=audit["completed_stages"], required_static=len(required))
        # All upstream native bytes, including unused heartbeat diagnostics,
        # are retained and hashed; no extraction, rewriting or invented receipts.
        entries = sorted(n for n in names if n.startswith(prefix)
                         and not n.startswith(quarantine))
        require(len(entries) == source["upstream_native_files"], "NATIVE_FILE_COUNT_DRIFT")
        manifest_path = folder / "native_entry_hashes.jsonl"
        aggregate = hashlib.sha256()
        native_bytes = 0
        file_start = time.perf_counter()
        with manifest_path.open("xb") as output:
            for index, name in enumerate(entries):
                h = hashlib.sha256()
                size = 0
                with archive.open(name) as stream:
                    while chunk := stream.read(65536):
                        h.update(chunk)
                        size += len(chunk)
                require(size == names[name].file_size, "NATIVE_ENTRY_SIZE_DRIFT")
                row = json.dumps({"name": name, "bytes": size, "raw_sha256": h.hexdigest()},
                                 sort_keys=True, separators=(",", ":")).encode() + b"\n"
                output.write(row)
                aggregate.update(row)
                native_bytes += size
                if (index + 1) % 1000 == 0:
                    output.flush()
                    os.fsync(output.fileno())
                    mark("NATIVE_FILE_HASH_PROGRESS", entries=index + 1, bytes=native_bytes)
            output.flush()
            os.fsync(output.fileno())
        require(native_bytes == source["upstream_native_bytes"], "NATIVE_BYTE_COUNT_DRIFT")
        actual_manifest = hashlib.sha256()
        with manifest_path.open("rb") as stream:
            while chunk := stream.read(65536):
                actual_manifest.update(chunk)
        require(actual_manifest.digest() == aggregate.digest(), "NATIVE_MANIFEST_PERSISTENCE_DRIFT")
        file_wall = time.perf_counter() - file_start
        mark("NATIVE_FILE_HASH_COMPLETE", entries=len(entries), bytes=native_bytes, wall_s=file_wall)
    return {"scope": "ARCHIVED_NATIVE_EVIDENCE_DEVELOPMENT_READBACK_ONLY",
        "source_formal_run_id": source["run_id"], "source_formal_run_gate": "INVALID_C3_C_EXECUTION",
        "source_run_context_explicit_not_process_environment_override": True,
        "completed_batches": audit["completed_batches"],
        "completed_stage_records": audit["completed_stages"],
        "required_static_stages_present": len(required),
        "raw_captures_verified": audit["raw_captures"], "native_files_hashed": len(entries),
        "native_bytes_hashed": native_bytes, "native_entry_manifest_sha256": aggregate.hexdigest(),
        "quarantined_failed_final_entries": len(quarantined),
        "official_zip_sha256": source["raw_sha256"], "official_zip_digest_wall_s": digest_wall,
        "optimized_native_audit_wall_s": audit_wall, "native_all_file_hash_wall_s": file_wall,
        "total_readback_wall_s": time.perf_counter() - started,
        "full_final_reproduction": False, "case_schema_aggregate_reproduction": False,
        "old_scores_borrowed_for_new_qualification": False, "candidate_execution": False,
        "formal_qualification": False}
