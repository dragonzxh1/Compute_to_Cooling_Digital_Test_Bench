"""Remote-only stdlib unit worker. Actual Windows Job release before testing."""
import os
import sys
import json
import time
import hashlib
import platform
import traceback
from pathlib import Path


def main():
    here=Path(__file__).resolve().parent
    repo=here.parents[3]
    out=Path(sys.argv[1]).resolve()
    if (os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("RUNNER_ENVIRONMENT")!="github-hosted" or
        os.environ.get("RUNNER_OS")!="Windows" or platform.node().upper()=="HIPPO" or
        not out.is_relative_to(repo/"artifacts/memphis-r12-mapping-v1")):
        raise RuntimeError("ISOLATED_REMOTE_UNIT_ONLY")
    def save(name,value):
        raw=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode()+b"\n"
        with (out/name).open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
    save("ready.json",dict(pid=os.getpid(),executable=sys.executable))
    deadline=time.monotonic()+25
    while not (out/"release.json").exists():
        if time.monotonic()>deadline: raise TimeoutError("RELEASE_TIMEOUT")
        time.sleep(.05)
    release=json.loads((out/"release.json").read_bytes())
    proof_raw=(out/"external_job_identity.json").read_bytes();proof=json.loads(proof_raw)
    if (release["actual_python_pid"]!=os.getpid() or proof["actual_python_pid"]!=os.getpid() or
        not proof["in_target_job"] or proof["cpu_rate"]!=2500 or proof["process_mb"]!=256 or
        proof["job_mb"]!=512 or release["external_proof_raw_sha256"]!=hashlib.sha256(proof_raw).hexdigest()):
        raise RuntimeError("ACTUAL_PYTHON_JOB_REQUIRED")
    if platform.python_version()!="3.11.9": raise RuntimeError("PYTHON_VERSION_DRIFT")
    manifest=json.loads((here/"source_manifest.json").read_bytes())
    def verify():
        for record in manifest["source_files"]:
            if hashlib.sha256((repo/record["path"]).read_bytes()).hexdigest()!=record["sha256"]:
                raise RuntimeError("SOURCE_DRIFT:"+record["path"])
    verify()
    environment=dict(source_commit=os.environ["GITHUB_SHA"],python=platform.python_version(),executable=sys.executable,
        image=os.environ.get("ImageVersion"),os=platform.platform(),pid=os.getpid(),
        scope="NEW_R12_STATIC_AND_UNIT_DEVELOPMENT_NOT_FORMAL_M1_ENVIRONMENT",cpu_rate=2500,process_mb=256,job_mb=512,
        wall_seconds=480,job_proof_sha256=hashlib.sha256(proof_raw).hexdigest(),long_simulation=False)
    save("environment_before.json",environment)
    result=dict(status="FAIL",scope="R12_UNIT_ONLY",source_commit=os.environ["GITHUB_SHA"])
    try:
        from .topology import build_topology
        from .tests import run_tests
        from .delivery import write_package
        intake=json.loads((here/"inputs/memphis_r12_pid_data_v1.json").read_bytes())
        graph=build_topology(intake)
        results=run_tests(graph)
        out_delivery=out/"delivery";out_delivery.mkdir()
        result["summary"]=write_package(graph,results,out_delivery,manifest,environment)
        if any(x["status"]!="PASS" for x in results):
            raise RuntimeError("UNIT_ASSERTION_FAILURE")
        verify();result["status"]="PASS"
    except BaseException as e:
        result.update(error=repr(e),traceback=traceback.format_exc())
        print(result["traceback"],flush=True)
    save("environment_after.json",environment)
    save("result.json",result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
