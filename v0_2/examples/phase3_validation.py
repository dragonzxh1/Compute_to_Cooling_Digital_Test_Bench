"""Reproduce the numerical tables used by PHASE3_THERMAL_REPORT.md; stdout JSON only."""

import json
import math

from v0_2.thermal.fixtures import (
    coldplate_model,
    flow,
    gpu_chain,
    insulated,
    linear_rc,
    pair,
    with_power,
)
from v0_2.thermal.harness import BoundaryEvent, convergence, run
from v0_2.thermal.integrator import Method

DTS = (200_000_000, 100_000_000, 50_000_000)


def main():
    analytic = []
    for name, fixture, duration, expected in (
        ("insulated", insulated(), 10_000_000_000, (310.0,)),
        ("boundary_rc", linear_rc(), 100_000_000_000, (300 + 20 * math.exp(-2),)),
        (
            "two_node_rc",
            pair(),
            200_000_000_000,
            (300 + 20 * math.exp(-6), 300 - 10 * math.exp(-6)),
        ),
    ):
        for method in Method:
            for dt in DTS:
                r = run(fixture, duration, dt, method)
                analytic.append(
                    {
                        "case": name,
                        "method": method.value,
                        "dt_s": dt / 1e9,
                        **r.metrics(),
                        "error_vs_closed_form_k": max(
                            abs(n.temperature_k - t) for n, t in zip(r.final_state.nodes, expected)
                        ),
                    }
                )
    refinement = {}
    for name in ("linear", "chain", "step"):
        f = linear_rc() if name == "linear" else gpu_chain(power=30 if name == "step" else 120)
        events = (
            ()
            if name != "step"
            else (BoundaryEvent(20_000_000_000, with_power(f, 120).sources, f.boundaries, f.flows),)
        )
        runs = [run(f, 100_000_000_000, dt, events=events) for dt in DTS]
        result = convergence(runs)
        exact = run(f, 100_000_000_000, DTS[0], Method.EXACT_LINEAR, events)
        result["final_error_vs_exact_k"] = [
            max(
                abs(a.temperature_k - b.temperature_k)
                for a, b in zip(r.final_state.nodes, exact.final_state.nodes)
            )
            for r in runs
        ]
        result["coarse_vs_finest"] = {
            key: abs(result["metrics"][0][key] - result["metrics"][-1][key])
            for key in ("peak_k", "min_headroom_k", "air_j", "liquid_j", "plate_to_liquid_j")
        }
        refinement[name] = result
    splits = {
        name: run(f, 100_000_000_000, DTS[1]).metrics()
        for name, f in (
            ("A", gpu_chain()),
            ("B_higher_liquid_R", gpu_chain(conduction_r=0.2)),
            ("C_lower_air_R", gpu_chain(air_r=0.2)),
        )
    }
    model = coldplate_model()
    coldplate = [
        {
            "flow_kg_s": m,
            "rth_k_w": model.resistance(flow(m)),
            "heat_w": model.evaluate(320, 300, flow(m)).heat_transfer_w,
            "validity": "VALID",
        }
        for m in (0.01, 0.05, 0.1, 0.2, 0.5)
    ]
    print(
        json.dumps(
            {
                "analytic": analytic,
                "refinement": refinement,
                "air_liquid": splits,
                "coldplate": coldplate,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
