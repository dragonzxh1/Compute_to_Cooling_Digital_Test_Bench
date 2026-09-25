"""Render Phase 5R2 target-authority evidence from the frozen JSON artifact."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "phase5_r2_selection_evidence.json"
OUTPUT = ROOT / "docs/results/phase5_r2_target_authority.png"


def render() -> Path:
    evidence = json.loads(SOURCE.read_text(encoding="utf-8"))
    authority = evidence["authority"]
    speeds = [authority["low_speed_fraction"], authority["high_speed_fraction"]]
    temperatures = [authority["t_low_k"], authority["t_high_k"]]
    target = authority["target_k"]

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    ax.plot(speeds, temperatures, marker="o", linewidth=2.4, color="#2166ac")
    ax.axhline(target, color="#b2182b", linewidth=2, label=f"Derived midpoint {target:.3f} K")
    ax.axhspan(
        target - 0.5,
        target + 0.5,
        color="#ef8a62",
        alpha=0.18,
        label="Future ±0.5 K qualification band",
    )
    ax.scatter(speeds, temperatures, s=90, color="#2166ac", zorder=3)
    annotations = ((18, -2, "left"), (-18, 10, "right"))
    for speed, value, label, (x_offset, y_offset, alignment) in zip(
        speeds,
        temperatures,
        ("Low authority", "High authority"),
        annotations,
    ):
        ax.annotate(
            f"{label}\n{speed:.1f} speed, {value:.3f} K",
            (speed, value),
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            ha=alignment,
            va="center",
        )
    ax.set_xlim(0.24, 0.96)
    ax.set_xlabel("Frozen pump speed fraction / cooling authority endpoint")
    ax.set_ylabel("Final-window mean maximum device temperature (K)")
    ax.set_title("Phase 5R2 target derived from frozen plant authority at 120 W/device")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.text(
        0.5,
        0.01,
        "Generic numerical fixture. Midpoint-derived research target; not an OEM/NVIDIA/GB300 thermal target.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.98))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=160)
    plt.close(fig)
    return OUTPUT


if __name__ == "__main__":
    print(render())
