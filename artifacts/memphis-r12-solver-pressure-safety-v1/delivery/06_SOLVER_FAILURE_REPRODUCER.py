"""Remote controlled entry only. Actual reproduction implementation is in source/.
Run through source/v0_2/tests/tools/memphis_r12_solver_pressure_safety_v1/run_remote.ps1 -Stage baseline.
The imported worker refuses local/non-Job execution before importing NumPy.
"""
from v0_2.tests.tools.memphis_r12_solver_pressure_safety_v1.worker import main
if __name__ == "__main__":
    raise SystemExit(main())
