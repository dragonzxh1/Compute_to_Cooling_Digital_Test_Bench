"""Thin pytest lifecycle logging. Existing test bodies/expectations stay intact."""
import os
import json
import pytest

from .admission import ROOT, admit
from .progress import Progress

_LOG = None
_REPORTS = []
_EXPECTED_COUNTS = {}


def pytest_configure(config):
    global _LOG, _EXPECTED_COUNTS
    admit()
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
        raise RuntimeError("DISABLE_UNREGISTERED_THIRD_PARTY_PLUGINS_FIRST")
    relative = os.environ.get("C2C_RECOVERY_PROGRESS_PATH")
    if not relative:
        raise RuntimeError("DEDICATED_PROGRESS_PATH_REQUIRED")
    # Independent scope selects only explicit existing test functions, not broad collection.
    plan = json.loads((ROOT / "v0_2/tests/tools/liquid_recovery_v1/plan.json").read_bytes())
    allowed = {node for stage in plan["smoke_stages"] for node in stage["pytest_node_ids"]}
    if not config.args or any(node not in allowed for node in config.args):
        raise RuntimeError("SMOKE_NODE_SELECTION_NOT_REGISTERED")
    if len(set(config.args)) != len(config.args):
        raise RuntimeError("DUPLICATE_SMOKE_NODE_SELECTION")
    _EXPECTED_COUNTS = {node: plan["expected_collection_counts"][node] for node in config.args}
    _LOG = Progress(relative)
    _LOG.mark("BEGIN", "PYTEST_SESSION")
    _LOG.mark("BEGIN", "SMOKE_COLLECTION")


def pytest_collection_finish(session):
    counts = {node: 0 for node in _EXPECTED_COUNTS}
    collected = []
    for item in session.items:
        node = item.path.relative_to(ROOT).as_posix() + "::" + item.originalname
        if node not in counts:
            pytest.exit("UNREGISTERED_COLLECTED_SMOKE_CASE", returncode=1)
        counts[node] += 1
        collected.append(item.nodeid)
    if counts != _EXPECTED_COUNTS or len(set(collected)) != len(collected):
        pytest.exit("SMOKE_COLLECTION_INCOMPLETE_OR_DUPLICATED", returncode=1)
    _LOG.mark("END", "SMOKE_COLLECTION", collected_count=len(collected))


def pytest_runtest_setup(item):
    _LOG.mark("BEGIN", "TEST_SETUP", case_id=item.nodeid)


def pytest_runtest_call(item):
    _LOG.mark("BEGIN", "TEST_CALL", case_id=item.nodeid)


def pytest_runtest_teardown(item, nextitem):
    _LOG.mark("BEGIN", "TEST_TEARDOWN", case_id=item.nodeid)


def pytest_runtest_logreport(report):
    # No exception repr/str, internal locals, raw sensors or future commands.
    _REPORTS.append({"case_id": report.nodeid, "phase": report.when, "outcome": report.outcome})
    _LOG.mark("END" if report.passed else "ERROR", "TEST_" + report.when.upper(),
              case_id=report.nodeid, outcome=report.outcome)
    if not report.passed:
        # -x alone does not stop on skip; skip/incomplete is not a recovery PASS.
        pytest.exit("FIRST_NON_PASS_SMOKE_STOP", returncode=1)


def pytest_sessionfinish(session, exitstatus):
    if _LOG is None:
        return
    try:
        admit()  # Fresh end-of-session source/environment verification.
        call_count = sum(report["phase"] == "call" for report in _REPORTS)
        if exitstatus == 0 and call_count != sum(_EXPECTED_COUNTS.values()):
            session.exitstatus = 1
            exitstatus = 1
        _LOG.mark("END" if exitstatus == 0 else "ERROR", "PYTEST_SESSION",
                  exitcode=int(exitstatus), report_count=len(_REPORTS))
    finally:
        _LOG.close()
