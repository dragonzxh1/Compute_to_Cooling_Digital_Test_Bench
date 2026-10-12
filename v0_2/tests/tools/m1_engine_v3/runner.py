"""Remote-development source lock API; no Python process-launch coordinator."""
import argparse
from .common import ROOT, read, guard
from .package_guard import environment


def source_lock():
    guard()
    from v0_2.tests.tools.m1_remote_control_v3.admission import manifest
    registration = manifest()
    hashes = dict(registration["bundle_entry_raw_hashes"])
    hashes.update(registration["remote_source_raw_hashes"])
    return {"mode": "DEVELOPMENT_ONLY_NOT_QUALIFICATION", "source_raw_hashes": hashes,
            "environment": environment()}


def capture(*args, **kwargs):
    raise RuntimeError("EXTERNAL_OWNED_JOB_COORDINATOR_REQUIRED")


def campaign(*args, **kwargs):
    raise RuntimeError("USE_VERSIONED_REMOTE_DEVELOPMENT_CAMPAIGN_NOT_FORMAL_ENTRY")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    if not args.development:
        parser.error('Formal execution is not authorized in this remote-development package.')
    campaign()


if __name__ == '__main__':
    main()
