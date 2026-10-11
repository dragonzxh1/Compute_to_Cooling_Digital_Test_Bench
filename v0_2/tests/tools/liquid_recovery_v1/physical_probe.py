"""Prepared 5 s physical-loop probe. No candidate or controller edits."""
import json
import os

from .admission import admit
from .progress import Progress


def main():
    admit()  # Before importing any plant computation.
    from v0_2.plant.fixtures import physical_fixture
    from v0_2.plant.loop import step
    from v0_2.plant.phase4_harness import PlantRun, run
    from v0_2.thermal.validity import SolverStatus

    log = Progress(os.environ["C2C_RECOVERY_PROGRESS_PATH"])
    try:
        log.mark("BEGIN", "PHYSICAL_PROBE")
        # Exact existing branch=2 case in test_full_secondary_loop_mass_energy_and_storage.
        log.mark("BEGIN", "PHYSICAL_FIXTURE", case_id="PHYSICAL-5S-BRANCH2")
        plant, controls = physical_fixture(2)
        state = plant.initial_state
        accepted = []
        log.mark("END", "PHYSICAL_FIXTURE", case_id="PHYSICAL-5S-BRANCH2")
        for tick in range(50):
            now = state.time_ns
            log.mark("BEGIN", "PHYSICAL_STEP", tick=tick, time_ns=now, dt_ns=100_000_000)
            result = step(plant, state, controls, 100_000_000)
            if result.solver_status != SolverStatus.CONVERGED:
                raise RuntimeError("PHYSICAL_STEP_NOT_CONVERGED")
            log.mark("END", "PHYSICAL_STEP", tick=tick, time_ns=result.next_state.time_ns)
            log.mark("BEGIN", "LEDGER_READ", tick=tick, time_ns=result.next_state.time_ns)
            log.mark("END", "LEDGER_READ", tick=tick, time_ns=result.next_state.time_ns,
                     energy_residual_j=result.ledger.full_loop_residual_j,
                     mass_volume_residual_kg_s=result.ledger.max_mass_volume_residual_kg_s,
                     pump_head_pa=result.hydraulic.pump_head_pa,
                     total_flow_m3_s=result.hydraulic.total_flow_m3_s,
                     hx_secondary_out_w=result.hx.secondary_out_w)
            accepted.append(result)
            state = result.next_state
        observed = PlantRun(plant.initial_state, tuple(accepted),
                            (plant, controls, 5_000_000_000, ()))
        log.mark("BEGIN", "INSTRUMENTATION_EQUIVALENCE")
        baseline = run(plant, controls, 5_000_000_000, 100_000_000)
        # Diagnostic equivalence, NOT output-derived golden behavioral expectations.
        if observed.states != baseline.states or tuple(s.ledger for s in observed.accepted) != tuple(
            s.ledger for s in baseline.accepted
        ):
            raise RuntimeError("LOGGED_PHYSICAL_PROBE_NOT_EQUIVALENT")
        log.mark("END", "INSTRUMENTATION_EQUIVALENCE")
        log.mark("BEGIN", "AGGREGATE_LEDGER")
        metrics = observed.metrics()
        if not metrics["energy_pass"] or not metrics["mass_pass"]:
            raise RuntimeError("EXISTING_PHYSICAL_LEDGER_GATE_FAIL")
        log.mark("END", "AGGREGATE_LEDGER", steps=metrics["steps"],
                 energy_residual_j=metrics["signed_energy_residual_j"],
                 final_cdu_supply_k=metrics["final_cdu_supply_k"])
        admit()
        log.mark("END", "PHYSICAL_PROBE")
        print(json.dumps({"status": "PASS", "scope": "PHYSICAL_LEDGER_SMOKE_ONLY",
                          "metrics": metrics, "formal_qualification": False}, allow_nan=False))
        return 0
    except BaseException:
        log.mark("ERROR", "PHYSICAL_PROBE")
        raise
    finally:
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
