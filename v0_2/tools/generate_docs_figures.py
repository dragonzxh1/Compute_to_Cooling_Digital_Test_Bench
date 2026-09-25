"""Generate selected GitHub figures from Phase 3/4.1/5 validation outputs."""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from v0_2.examples.phase4_1_validation import evidence as phase4_1_evidence
from v0_2.examples.phase5_evidence import OUT
from v0_2.plant.fixtures import physical_fixture
from v0_2.thermal.coldplate import FlowInput
from v0_2.thermal.fixtures import coldplate_model
from v0_2.thermal.provenance import fixture_parameter as p

CAPTION = "Generic numerical fixture / unvalidated hardware parameters"


def _save(fig, name):
    fig.text(0.5, 0.005, CAPTION, ha="center", fontsize=9, color="#874b1c")
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _architecture():
    boxes = [
        ("IT power", 50, 40), ("Device thermal", 210, 40), ("Coldplate", 370, 40),
        ("Branch hydraulics", 530, 40), ("CDU / HX", 690, 40), ("FWS", 850, 40),
        ("Measurement", 690, 145), ("Outer feedback", 490, 145),
        ("Supervisor", 310, 145), ("Local PLC", 150, 145), ("Pump actuator", 10, 145),
    ]
    chunks = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="260" viewBox="0 0 1020 260">',
        '<style>text{font:14px Arial;fill:#17324d}.box{fill:#e8f2fa;stroke:#2673a4;stroke-width:2}.arrow{stroke:#347e61;stroke-width:2;fill:none;marker-end:url(#tip)}</style>',
        '<defs><marker id="tip" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#347e61"/></marker></defs>',
    ]
    for label, x, y in boxes:
        chunks.append(f'<rect class="box" x="{x}" y="{y}" width="130" height="45" rx="7"/><text x="{x+65}" y="{y+28}" text-anchor="middle">{label}</text>')
    for x1, y1, x2, y2 in ((180,62,210,62),(340,62,370,62),(500,62,530,62),(660,62,690,62),(820,62,850,62),(745,85,745,145),(690,167,620,167),(490,167,440,167),(310,167,280,167),(150,167,140,167),(75,145,75,100),(75,100,530,100)):
        chunks.append(f'<path class="arrow" d="M{x1} {y1}L{x2} {y2}"/>')
    chunks.append(f'<text x="510" y="238" text-anchor="middle">{CAPTION}; feedback-only Phase 5 (Phase 6 feedforward not implemented)</text></svg>')
    (OUT / "system_architecture.svg").write_text("".join(chunks), encoding="utf-8")


def _coldplate():
    model = coldplate_model()
    flows = np.linspace(0.01, 0.2, 60)
    rth = [model.resistance(FlowInput(p("figure.flow", float(x), "kg/s"), "fixture_water")) for x in flows]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(flows, rth, linewidth=2)
    ax.set(xlabel="Local mass flow (kg/s)", ylabel="Coldplate Rth (K/W)", title="Phase 3 coldplate Rth(flow)")
    ax.grid(alpha=.25)
    _save(fig, "coldplate_rth_flow.png")


def _operating_point():
    plant, _ = physical_fixture()
    curve = plant.pump_curve
    graph = plant.hydraulic_graph
    branch_k = [sum(e.coefficient.value for e in branch) for branch in graph.branches]
    equivalent_k = 1 / sum(1 / np.sqrt(k) for k in branch_k) ** 2
    system_k = equivalent_k + sum(e.coefficient.value for e in (*graph.supply_series, *graph.return_series))
    flow = np.linspace(0, 0.00035, 100)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(flow * 1000, system_k * flow**2, label="System curve", color="#263d55")
    for speed in (.5, .9):
        head = np.maximum(0, curve.shutoff_head_pa.value * speed**2 - curve.curve_k.value * flow**2)
        point = np.sqrt(curve.shutoff_head_pa.value * speed**2 / (system_k + curve.curve_k.value))
        ax.plot(flow * 1000, head, label=f"Pump curve, speed {speed}")
        ax.scatter([point * 1000], [system_k * point**2], s=55)
    ax.set(xlabel="Total mass flow (kg/s)", ylabel="Pressure rise (Pa)", title="Phase 4 pump/system intersections")
    ax.legend()
    ax.grid(alpha=.25)
    _save(fig, "hydraulic_operating_point.png")


def _authority(data):
    speeds = sorted(float(x) for x in data["sweep"])
    fields = (("branch_mass_flow_kg_s", "Branch flow (kg/s)"), ("coldplate_rth_k_w", "Rth (K/W)"), ("window_plate_to_coolant_w", "Plate-to-liquid Q (W)"), ("window_device_k", "Device temperature (K)"))
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (field, label) in zip(axes.flat, fields):
        ax.plot(speeds, [data["sweep"][str(x)]["b0"][field] for x in speeds], marker="o")
        ax.set(xlabel="Actual pump speed (fraction)", ylabel=label)
        ax.grid(alpha=.25)
    fig.suptitle("Phase 4.1 measured control-authority chain")
    _save(fig, "phase4_1_control_authority.png")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fields = (("branch_mass_flow_kg_s", "Flow (kg/s)"), ("coldplate_rth_k_w", "Rth (K/W)"), ("window_device_k", "Device T (K)"))
    for ax, (field, label) in zip(axes, fields):
        for case, info in data["restriction"].items():
            ax.plot((0, 1), [info[b][field] for b in ("b0", "b1")], marker="o", label=case)
        ax.set(xticks=(0, 1), xticklabels=("restricted b0", "unrestricted b1"), ylabel=label)
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Phase 4.1 branch restriction: K of b0 x1.5")
    _save(fig, "branch_restriction.png")


def _phase5(data):
    rows = data["holdout"]["rows"]
    time = np.array([r["time_ns"] / 1e9 for r in rows])
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(time, [r["device_k"] for r in rows], label="True device (audit only)")
    axes[0].plot(time, [r["measured_device_k"] for r in rows], label="Released measured device", alpha=.7)
    axes[0].axhline(data["baseline"]["thermal_control_target_k"], linestyle="--", color="red", label="Control target")
    axes[0].set_ylabel("Temperature (K)")
    axes[0].legend(fontsize=8)
    axes[1].plot(time, [r["requested_dp_pa"] for r in rows], label="Requested DP")
    axes[1].plot(time, [r["accepted_dp_pa"] for r in rows], label="Accepted DP")
    axes[1].plot(time, [r["measured_dp_pa"] for r in rows], label="Measured DP")
    axes[1].set_ylabel("DP (Pa)")
    axes[1].legend(fontsize=8)
    axes[2].plot(time, [r["pump_command"] for r in rows], label="Commanded")
    axes[2].plot(time, [r["pump_actual"] for r in rows], label="Actual")
    axes[2].plot(time, [r["pump_measured"] for r in rows], label="Measured", alpha=.7)
    axes[2].set_ylabel("Pump speed")
    axes[2].legend(fontsize=8)
    axes[3].plot(time, [r["total_flow_kg_s"] for r in rows])
    axes[3].set(xlabel="Time (s)", ylabel="Flow (kg/s)")
    for ax in axes:
        ax.grid(alpha=.25)
        for x in (10, 25, 40):
            ax.axvline(x, color="gray", linestyle=":", alpha=.5)
    fig.suptitle("Phase 5 feedback-only combined holdout")
    _save(fig, "phase5_closed_loop_holdout.png")
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = [r["safety_state"] for r in rows]
    states = {name: i for i, name in enumerate(sorted(set(labels)))}
    ax.step(time, [states[x] for x in labels], where="post", label="Safety state")
    ax.set(yticks=list(states.values()), yticklabels=list(states), xlabel="Time (s)", title="Phase 5 safety state timeline")
    ax.grid(alpha=.25)
    _save(fig, "safety_state_timeline.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    evidence_file = OUT / "phase5_evidence.json"
    if not evidence_file.exists():
        raise RuntimeError("Run python -m v0_2.examples.phase5_evidence first")
    phase5 = json.loads(evidence_file.read_text(encoding="utf-8"))
    phase4_1 = phase4_1_evidence()
    (OUT / "phase4_1_figure_source.json").write_text(json.dumps(phase4_1, indent=2) + "\n", encoding="utf-8")
    _architecture()
    _coldplate()
    _operating_point()
    _authority(phase4_1)
    _phase5(phase5)
    print("Generated figures in", OUT)


if __name__ == "__main__":
    main()
