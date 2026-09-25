"""Render the Phase 5.1R2 nominal qualification figure from frozen evidence."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "phase5_1r2_nominal_result.json"
OUTPUT = ROOT / "docs/results/phase5_1r2_nominal_regulation.png"
TARGET = 313.71072595542387


def series(rows, key):
    return [row[key] for row in rows]


def main() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    fig, axes = plt.subplots(3, 2, figsize=(15, 12), sharex=True)
    colors = {"WARM_CAPTURE": "#d1495b", "COLD_CAPTURE": "#00798c"}
    states = {"FF_DISABLED": 0, "NORMAL": 1, "DEGRADED": 2, "DERATE_REQUESTED": 3, "PROTECTED": 4, "FAULT": 5}
    rth_ax = axes[1, 1].twinx()
    for label, rows in result["figure_traces"].items():
        t = series(rows, "time_s")
        color = colors[label]
        axes[0, 0].plot(t, series(rows, "measured_device_k"), color=color, label=label)
        axes[0, 1].plot(t, series(rows, "requested_dp_pa"), color=color, linestyle=":", label=f"{label} requested")
        axes[0, 1].plot(t, series(rows, "accepted_dp_pa"), color=color, label=f"{label} accepted")
        axes[0, 1].plot(t, series(rows, "measured_dp_pa"), color=color, linestyle="--", alpha=0.75, label=f"{label} measured")
        axes[1, 0].plot(t, series(rows, "pump_command"), color=color, linestyle=":", label=f"{label} command")
        axes[1, 0].plot(t, series(rows, "pump_actual"), color=color, label=f"{label} actual")
        axes[1, 0].plot(t, series(rows, "pump_measured"), color=color, linestyle="--", alpha=0.75, label=f"{label} measured")
        axes[1, 1].plot(t, series(rows, "branch_flow_kg_s"), color=color, label=f"{label} branch flow")
        rth_ax.plot(t, series(rows, "coldplate_rth_k_w"), color=color, linestyle="--", alpha=0.55)
        axes[2, 0].step(t, [states.get(x, 6) for x in series(rows, "safety_state")], where="post", color=color, label=label)
        axes[2, 1].plot(t, [value - TARGET if value is not None else None for value in series(rows, "measured_device_k")], color=color, label=label)

    axes[0, 0].axhspan(TARGET - 0.5, TARGET + 0.5, color="#7fb069", alpha=0.18, label="target band")
    axes[0, 0].axhline(TARGET, color="black", linewidth=1, linestyle="--", label="target")
    axes[0, 0].set_ylabel("Measured max device T (K)")
    axes[0, 0].set_title("1. Temperature capture from both sides")
    axes[0, 1].set_ylabel("DP (Pa)")
    axes[0, 1].set_title("2. Requested / accepted / measured DP")
    axes[1, 0].axhline(0.3, color="gray", linewidth=0.8)
    axes[1, 0].axhline(0.9, color="gray", linewidth=0.8)
    axes[1, 0].set_ylabel("Pump speed (fraction)")
    axes[1, 0].set_title("3. Pump command / actual / measured")
    axes[1, 1].set_ylabel("Branch flow (kg/s)")
    rth_ax.set_ylabel("Coldplate Rth (K/W)")
    axes[1, 1].set_title("4. Branch flow and coldplate Rth")
    axes[2, 0].set_yticks(list(states.values()), list(states))
    axes[2, 0].set_ylabel("Safety state")
    axes[2, 0].set_title("5. Safety state")
    axes[2, 1].axhspan(-0.5, 0.5, color="#7fb069", alpha=0.18)
    axes[2, 1].axhline(0, color="black", linewidth=1, linestyle="--")
    axes[2, 1].set_ylabel("Measured T error (K)")
    axes[2, 1].set_title("6. Control error")
    for ax in axes.flat:
        ax.grid(alpha=0.2)
        ax.set_xlabel("Qualification time (s)")
        ax.legend(fontsize=7, loc="best")
    fig.suptitle(
        "Phase 5.1R2 Final Frozen Feedback Nominal Regulation Qualification\n"
        "Generic numerical fixture. Frozen Phase 5R2 feedback baseline. Not OEM/NVIDIA/GB300 validation.",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180)
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    main()
