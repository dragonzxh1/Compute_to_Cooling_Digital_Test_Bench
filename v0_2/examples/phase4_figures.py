"""Bilingual figures for the frozen Phase 4 physical-plant evidence.

Every series plotted here is read from the same generic, uncalibrated fixture that
`phase4_validation.py` reports, and the tabulated values in
`PHASE4_PHYSICAL_PLANT_REPORT.md` remain the authoritative record. These figures
visualise that evidence; they add no claims, and none of them is a GB300 or OEM
measurement.

Run from the repository root (writes to `figures/phase4/`):

    python -m v0_2.examples.phase4_figures [output-directory]

Matplotlib is an optional extra, not a runtime dependency of the isolated V0.2
distribution: `python -m pip install -e "./v0_2[figures]"`.
"""

import sys
import warnings
from collections import namedtuple
from dataclasses import replace
from math import exp, fsum
from pathlib import Path

from v0_2.coolant.advection import AdvectiveLink, solve_implicit
from v0_2.hydraulics.pump import pump_energy
from v0_2.hydraulics.solver import solve
from v0_2.plant.fixtures import generic_fluid, physical_fixture, volume
from v0_2.plant.phase4_harness import PlantEvent, convergence, run
from v0_2.thermal.provenance import fixture_parameter as p

# Same candidate order as the V0.1 plotting module, so both trees resolve CJK text
# identically. Bilingual labels mean a CJK face is always required.
_CJK_FONT_CANDIDATES = (
    "Noto Sans CJK SC",
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
)

DISCLAIMER = (
    "通用未标定数值夹具，非 GB300/OEM 测量 / "
    "Generic uncalibrated numerical fixture, not a GB300/OEM measurement"
)

BLUE, ORANGE, GREEN, RED, PURPLE, GREY = (
    "#3766a3",
    "#d26a2e",
    "#3f8f5f",
    "#b4463f",
    "#7a5aa8",
    "#777777",
)

DT_MESHES = (200_000_000, 100_000_000, 50_000_000)

Backend = namedtuple("Backend", "mpl figure canvas")


def load_backend():
    try:
        import matplotlib as mpl
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            "Phase 4 figures need matplotlib, which is an optional extra rather than a\n"
            "runtime dependency of the isolated V0.2 distribution. Install it with:\n"
            '    python -m pip install -e "./v0_2[figures]"'
        ) from exc
    return Backend(mpl, Figure, FigureCanvasAgg)


def cjk_font(mpl):
    installed = {font.name for font in mpl.font_manager.fontManager.ttflist}
    for candidate in _CJK_FONT_CANDIDATES:
        if candidate in installed:
            return candidate
    raise SystemExit(
        "Bilingual figures require a CJK font; install Noto Sans CJK, Microsoft YaHei, "
        "SimHei, or WenQuanYi Zen Hei"
    )


def figure(backend, title, size=(12.0, 7.0)):
    drawn = backend.figure(figsize=size, layout="constrained")
    backend.canvas(drawn)
    drawn.suptitle(title, fontsize=12.5, fontweight="bold")
    return drawn, drawn.subplots(1, 2, squeeze=False)[0]


def finish(drawn, backend, output, name):
    # `supxlabel` is laid out by constrained layout, so the disclaimer cannot
    # overlap the axes the way a raw `fig.text` would.
    drawn.supxlabel(DISCLAIMER, fontsize=6.5, color="#666666")
    path = output / name
    drawn.savefig(path, dpi=150)
    print(f"wrote {path}")
    return path


def times(plant_run):
    return [state.time_ns / 1e9 for state in plant_run.states]


def temperature(plant_run, node_id):
    return [state.by_id[node_id].temperature_k for state in plant_run.states]


def step_end_times(plant_run):
    return [state.time_ns / 1e9 for state in plant_run.states[1:]]


def cumulative(plant_run, field):
    """Cumulative ledger field, one value per state including the zero initial one."""
    total, series = 0.0, [0.0]
    for result in plant_run.accepted:
        total += getattr(result.ledger, field)
        series.append(total)
    return series


def hydraulic_figure(backend, output):
    """Figure 1: pump/system operating point and the branch flow split."""
    drawn, (left, right) = figure(
        backend,
        "图 1 水力网络：泵工作点与支路分流 / Figure 1 — Hydraulic network: "
        "pump operating point and branch split",
    )
    curve = physical_fixture(1)[0].pump_curve
    shutoff = curve.shutoff_head_pa.value
    k_pump = curve.curve_k.value

    # The pump map reaches zero head far inside the declared flow range. Sweeping
    # the whole declared range would clamp every speed to zero past that point and
    # flatten the interesting region into the left edge of the axes.
    q_zero = (shutoff / k_pump) ** 0.5
    swept = [q_zero * index / 200 for index in range(201)]
    for speed, colour in ((0.5, GREEN), (0.7, PURPLE), (0.9, BLUE), (1.0, ORANGE)):
        points = [(q, shutoff * speed**2 - k_pump * q**2) for q in swept]
        points = [(q, head) for q, head in points if head >= 0]
        left.plot(
            [q * 1000 for q, _ in points],
            [head / 1000 for _, head in points],
            color=colour,
            linewidth=1.4,
            label=f"泵曲线 pump, {speed:.1f}×",
        )
    for count, colour in ((1, BLUE), (2, ORANGE), (4, GREEN)):
        plant, _ = physical_fixture(count)
        points = [
            solve(plant.hydraulic_graph, plant.pump_curve, step / 100, 1000)
            for step in range(20, 101, 5)
        ]
        left.plot(
            [point.total_flow_m3_s * 1000 for point in points],
            [point.pump_head_pa / 1000 for point in points],
            marker="o",
            markersize=3.2,
            linewidth=1.1,
            color=colour,
            label=f"系统曲线 system, {count} 支路 branch",
        )
    plant, _ = physical_fixture(2)
    reported = solve(plant.hydraulic_graph, plant.pump_curve, 0.9, 1000)
    left.plot(
        [reported.total_flow_m3_s * 1000],
        [reported.pump_head_pa / 1000],
        marker="*",
        markersize=15,
        color=RED,
        linestyle="none",
        label="报告工况 reported point, 0.9×",
    )
    left.set_xlabel("体积流量 Volume flow Q (L/s)")
    left.set_ylabel("压头 / 压降 Head / ΔP (kPa)")
    left.set_title("泵曲线与系统曲线交点 / pump ∩ system", fontsize=10)
    left.set_xlim(0.0, q_zero * 1000 * 1.05)
    left.legend(fontsize=7, loc="upper right")
    left.grid(alpha=0.3)

    labels, values, colours = [], [], []
    for count, multiplier in ((1, None), (2, None), (2, 1.5), (4, None)):
        fixture, _ = physical_fixture(count, branch_multiplier=multiplier)
        result = solve(fixture.hydraulic_graph, fixture.pump_curve, 0.9, 1000)
        for index, flow in enumerate(result.branch_flows_m3_s):
            labels.append(f"{count}支路×{multiplier or 1.0:.1f}\n支路 {index}")
            values.append(flow * 1000)
            colours.append(RED if multiplier else BLUE)
    right.bar(range(len(values)), values, color=colours)
    right.set_xticks(range(len(values)))
    right.set_xticklabels(labels, fontsize=6.5)
    right.set_ylabel("支路质量流量 Branch mass flow (kg/s)")
    right.set_title("支路分流（红 = 0 号支路 K×1.5 受限）/ branch split", fontsize=10)
    right.grid(alpha=0.3, axis="y")
    return finish(drawn, backend, output, "01_hydraulic_network.png")


def transport_figure(backend, output):
    """Figure 2: one-cell transport against its analytic reference."""
    drawn, (left, right) = figure(
        backend,
        "图 2 冷却液输运：对解析解的 dt 收敛 / "
        "Figure 2 — Coolant transport: dt convergence to the analytic reference",
    )
    fluid = generic_fluid()
    links = (
        AdvectiveLink("in", "inlet", "cell", 0.2, "in"),
        AdvectiveLink("out", "cell", "outlet", 0.2, "out"),
    )
    inlet, mass, m_dot, span = 310.0, 1.0, 0.2, 5.0
    sample = [span * index / 250 for index in range(251)]
    analytic = [inlet - 10 * exp(-m_dot * t / mass) for t in sample]
    left.plot(
        sample,
        analytic,
        color=GREY,
        linewidth=1.6,
        linestyle="--",
        label="解析 analytic T = Tin + (T0 - Tin) e^(-m_dot t / M)",
    )
    errors, meshes = [], []
    for dt, colour in zip((0.2, 0.1, 0.05), (BLUE, ORANGE, GREEN)):
        state = volume("cell", fluid, mass=mass)
        held, series = [0.0], [state.temperature_k]
        for step in range(round(span / dt)):
            state = solve_implicit(
                (state,), links, dt, {"inlet": fluid.h(inlet), "outlet": fluid.h(300)}
            ).volumes[0]
            held.append((step + 1) * dt)
            series.append(state.temperature_k)
        left.plot(held, series, color=colour, linewidth=1.2, label=f"数值 numerical dt={dt:g}s")
        errors.append(abs(series[-1] - analytic[-1]))
        meshes.append(dt)
    left.set_xlabel("时间 Time (s)")
    left.set_ylabel("单胞温度 One-cell temperature (K)")
    left.set_title("一阶蓄热响应 / first-order storage", fontsize=10)
    left.legend(fontsize=7)
    left.grid(alpha=0.3)

    right.loglog(meshes, errors, marker="o", color=BLUE, label="|误差| at t=5 s")
    right.loglog(
        meshes,
        [errors[0] * (mesh / meshes[0]) for mesh in meshes],
        linestyle="--",
        color=GREY,
        label="一阶参考 O(dt)",
    )
    right.invert_xaxis()
    right.margins(x=0.3, y=0.2)
    for mesh, error in zip(meshes, errors):
        right.annotate(
            f"{error:.4f} K",
            (mesh, error),
            fontsize=7,
            textcoords="offset points",
            xytext=(4, 6),
        )
    right.set_xlabel("步长 dt Time step (s)")
    right.set_ylabel("末端绝对误差 |error| (K)")
    right.set_title("误差随 dt 下降 / error falls with dt", fontsize=10)
    right.legend(fontsize=7)
    right.grid(alpha=0.3, which="both")
    return finish(drawn, backend, output, "02_transport_convergence.png")


def temperature_chain_figure(backend, output):
    """Figure 3: die -> package -> plate -> local coolant -> CDU supply."""
    drawn, (left, right) = figure(
        backend,
        "图 3 耦合温度链 / Figure 3 — Coupled temperature chain",
        size=(12.0, 6.0),
    )
    plant, controls = physical_fixture(2)
    result = run(plant, controls, 5_000_000_000, 200_000_000)
    held = times(result)
    supply = temperature(result, "cdu")
    # The die carries nearly the whole gradient, so absolute temperatures bury
    # package, plate and coolant on top of one another. The rise above the CDU
    # supply separates the chain onto one readable scale instead.
    for node_id, label, colour in (
        ("b0:die", "裸片 die", ORANGE),
        ("b0:package", "封装 package", BLUE),
        ("b0:plate", "冷板 cold plate", GREEN),
        ("b0:local", "局部冷却液 local coolant", PURPLE),
    ):
        rise = [value - base for value, base in zip(temperature(result, node_id), supply)]
        left.plot(held, rise, color=colour, linewidth=1.5, label=label)
    left.set_xlabel("时间 Time (s)")
    left.set_ylabel("相对 CDU 供液的温升 Rise above CDU supply (K)")
    left.set_title("温升链 die→package→plate→coolant / rise chain", fontsize=10)
    left.legend(fontsize=8)
    left.grid(alpha=0.3)

    for node_id, label, colour in (
        ("b0:die", "裸片 die", ORANGE),
        ("cdu", "CDU 供液 CDU supply", RED),
        ("return_1", "回液 return", BLUE),
    ):
        right.plot(held, temperature(result, node_id), color=colour, linewidth=1.5, label=label)
    right.set_xlabel("时间 Time (s)")
    right.set_ylabel("绝对温度 Absolute temperature (K)")
    right.set_title("2 支路、每支路 120 W、泵速 0.9 / cold-start drift", fontsize=10)
    right.legend(fontsize=8, loc="center left")
    right.grid(alpha=0.3)

    metrics = result.metrics()
    right.annotate(
        f"峰值 peak {metrics['peak_k']:.3f} K\n"
        f"末态裸片 final die {metrics['final_die_k']:.3f} K\n"
        f"末态 CDU 供液 final supply {metrics['final_cdu_supply_k']:.3f} K\n"
        f"最大残差 max residual {metrics['max_residual_w']:.2e} W\n"
        f"守恒 energy/mass: {metrics['energy_pass']}/{metrics['mass_pass']}",
        xy=(0.03, 0.95),
        xycoords="axes fraction",
        fontsize=8.5,
        verticalalignment="top",
    )
    return finish(drawn, backend, output, "03_temperature_chain.png")


def energy_ledger_figure(backend, output):
    """Figure 4: full-loop energy ledger and its per-step closure residual."""
    drawn, (left, right) = figure(
        backend,
        "图 4 全回路能量账与残差 / Figure 4 — Full-loop energy ledger and residual",
    )
    plant, controls = physical_fixture(2)
    result = run(plant, controls, 5_000_000_000, 200_000_000)
    held = times(result)
    for field, label, colour in (
        ("source_j", "IT 注入 IT source", ORANGE),
        ("hx_export_j", "HX 排出 HX export", BLUE),
        ("stored_change_j", "储能变化 stored change", GREEN),
        ("pump_heat_liquid_j", "泵热入液 pump heat to liquid", PURPLE),
        ("air_export_j", "空气排出 air export", RED),
    ):
        left.plot(held, cumulative(result, field), color=colour, linewidth=1.6, label=label)
    left.axhline(0.0, color=GREY, linewidth=0.8, linestyle=":")
    left.set_xlabel("时间 Time (s)")
    left.set_ylabel("累计能量 Cumulative energy (J)")
    left.set_title("ΔE = E_IT + E_泵入液 − E_空气 − E_HX", fontsize=10)
    left.legend(fontsize=8)
    left.grid(alpha=0.3)

    residual_w = [
        abs(accepted.ledger.full_loop_residual_j)
        / ((accepted.next_state.time_ns - before.time_ns) / 1e9)
        for before, accepted in zip(result.states, result.accepted)
    ]
    right.semilogy(step_end_times(result), residual_w, marker="o", markersize=3,
                   color=BLUE, linewidth=1.1)
    metrics = result.metrics()
    right.axhline(metrics["max_residual_w"], color=RED, linestyle="--", linewidth=1.0,
                  label=f"最大 max {metrics['max_residual_w']:.2e} W")
    right.axhline(metrics["p95_residual_w"], color=GREEN, linestyle=":", linewidth=1.0,
                  label=f"P95 {metrics['p95_residual_w']:.2e} W")
    right.set_xlabel("时间 Time (s)")
    right.set_ylabel("单步残差率 Per-step residual rate (W)")
    right.set_title("每步闭合残差 / per-step closure", fontsize=10)
    right.legend(fontsize=7.5)
    right.grid(alpha=0.3, which="both")
    return finish(drawn, backend, output, "04_energy_ledger.png")


def fws_disturbance_figure(backend, output):
    """Figure 5: CDU supply temperature and HX export under FWS disturbance."""
    drawn, (left, right) = figure(
        backend,
        "图 5 FWS 扰动响应（5 s 时施加）/ "
        "Figure 5 — FWS disturbance response (applied at 5 s)",
    )
    plant, controls = physical_fixture(2)
    cases = (
        ("基线 baseline 290 K / 0.4 kg/s", None, BLUE),
        (
            "FWS 入口 290→294 K inlet",
            replace(controls, fws_inlet_temperature=p("FWS_warm", 294, "K")),
            ORANGE,
        ),
        (
            "FWS 流量 0.4→0.28 kg/s flow",
            replace(controls, primary_mass_flow=p("FWS_reduced", 0.28, "kg/s")),
            GREEN,
        ),
    )
    for label, after, colour in cases:
        events = () if after is None else (PlantEvent(5_000_000_000, after),)
        result = run(plant, controls, 10_000_000_000, 200_000_000, events)
        left.plot(times(result), temperature(result, "cdu"), color=colour,
                  linewidth=1.5, label=label)
        right.plot(step_end_times(result), [a.hx.secondary_out_w for a in result.accepted],
                   color=colour, linewidth=1.5, label=label)
    for axis in (left, right):
        axis.axvline(5.0, color=GREY, linestyle="--", linewidth=1.0)
        axis.set_xlabel("时间 Time (s)")
        axis.legend(fontsize=7.5)
        axis.grid(alpha=0.3)
    left.set_ylabel("CDU 供液温度 CDU supply (K)")
    left.set_title("CDU 有限蓄热，不跳变 / finite inventory, no step", fontsize=10)
    right.set_ylabel("HX 二次侧换热 HX secondary export (W)")
    right.set_title("HX 出口功率 / HX outlet power", fontsize=10)
    return finish(drawn, backend, output, "05_fws_disturbance.png")


def dt_convergence_figure(backend, output):
    """Figure 6: mesh refinement against the frozen tolerances."""
    drawn, (left, right) = figure(
        backend,
        "图 6 网格收敛 / Figure 6 — Mesh (dt) convergence on the coupled plant",
    )
    fixture, controls = physical_fixture(2, power_each=120)
    runs = [run(fixture, controls, 5_000_000_000, dt) for dt in DT_MESHES]
    report = convergence(runs)
    for result, dt, colour in zip(runs, DT_MESHES, (BLUE, ORANGE, GREEN)):
        left.plot(times(result), temperature(result, "b0:die"), color=colour,
                  linewidth=1.3, label=f"dt={dt / 1e9:g}s")
    left.set_xlabel("时间 Time (s)")
    left.set_ylabel("裸片温度 Die temperature (K)")
    left.set_title(f"2 支路裸片轨迹，收敛 {report['status']} / die trajectory", fontsize=10)
    left.legend(fontsize=8)
    left.grid(alpha=0.3)

    keys = list(report["tolerances"])
    differences = report["adjacent_differences"]
    positions = list(range(len(keys)))
    right.bar([i - 0.2 for i in positions],
              [differences[0][k] / report["tolerances"][k] for k in keys],
              width=0.38, color=BLUE, label="粗→中 coarse→medium")
    right.bar([i + 0.2 for i in positions],
              [differences[1][k] / report["tolerances"][k] for k in keys],
              width=0.38, color=ORANGE, label="中→细 medium→fine")
    right.axhline(1.0, color=RED, linestyle="--", linewidth=1.2, label="冻结容差 tolerance")
    right.set_yscale("log")
    right.set_xticks(positions)
    right.set_xticklabels(keys, rotation=35, ha="right", fontsize=6.5)
    right.set_ylabel("差异 ÷ 容差 difference ÷ tolerance")
    right.set_title("全部低于 1 = 通过 / all below 1 = pass", fontsize=10)
    right.legend(fontsize=7.5)
    right.grid(alpha=0.3, axis="y", which="both")
    return finish(drawn, backend, output, "06_dt_convergence.png")


def pump_energy_figure(backend, output):
    """Figure 7: pump electrical energy split by loss stage and destination.

    The stage split is summed from `pump_energy` per accepted step rather than
    re-derived from the drive efficiencies here, so it cannot silently disagree
    with the ledger the plant posted.
    """
    drawn, (left, right) = figure(
        backend,
        "图 7 泵电能分解 / Figure 7 — Pump electrical energy split",
        size=(12.0, 6.0),
    )
    plant, controls = physical_fixture(2)
    result = run(plant, controls, 5_000_000_000, 200_000_000)
    electrical = hydraulic = vfd = motor = internal = 0.0
    for before, accepted in zip(result.states, result.accepted):
        dt_s = (accepted.next_state.time_ns - before.time_ns) / 1e9
        stage = pump_energy(
            plant.pump_drive,
            accepted.hydraulic.pump_head_pa,
            accepted.hydraulic.total_flow_m3_s,
            dt_s,
        )
        electrical += stage.electrical_energy_j
        hydraulic += stage.hydraulic_w * dt_s
        vfd += stage.vfd_loss_w * dt_s
        motor += stage.motor_loss_w * dt_s
        internal += stage.internal_loss_w * dt_s
    ledgers = [result.ledger for result in result.accepted]
    to_liquid = fsum(item.pump_heat_liquid_j for item in ledgers)
    to_ambient = fsum(item.pump_heat_ambient_j for item in ledgers)

    # A single stacked bar renders as one full-width band and cannot be read, so
    # each stage is its own labelled bar.
    stages = (
        ("液压\nhydraulic", hydraulic, BLUE),
        ("泵内部\ninternal", internal, GREEN),
        ("电机\nmotor", motor, ORANGE),
        ("VFD", vfd, PURPLE),
    )
    left.bar(range(len(stages)), [value for _, value, _ in stages],
             color=[colour for _, _, colour in stages])
    for index, (_, value, _) in enumerate(stages):
        left.annotate(f"{value:.3f} J", (index, value), ha="center", va="bottom", fontsize=8.5)
    left.set_xticks(range(len(stages)))
    left.set_xticklabels([label for label, _, _ in stages], fontsize=8.5)
    left.set_ylim(0.0, hydraulic * 1.18)
    left.set_ylabel("能量 Energy (J)")
    left.set_title(f"总电能 {electrical:.3f} J 的构成 / composition", fontsize=10)
    left.grid(alpha=0.3, axis="y")

    destinations = (("入液\nto liquid", to_liquid, RED), ("入环境\nto ambient", to_ambient, GREY))
    right.bar(range(len(destinations)), [value for _, value, _ in destinations],
              color=[colour for _, _, colour in destinations])
    for index, (_, value, _) in enumerate(destinations):
        right.annotate(f"{value:.3f} J", (index, value), ha="center", va="bottom", fontsize=8.5)
    right.axhline(electrical, color=BLUE, linestyle="--", linewidth=1.2,
                  label=f"总电能 electrical {electrical:.3f} J")
    right.set_xticks(range(len(destinations)))
    right.set_xticklabels([label for label, _, _ in destinations], fontsize=8.5)
    right.set_ylim(0.0, electrical * 1.18)
    right.set_ylabel("能量 Energy (J)")
    right.set_title("去向分配（含被动水力耗散）/ destination split", fontsize=10)
    # The bars reach high enough to sit under a lower-right legend.
    right.legend(fontsize=7.5, loc="upper left")
    right.grid(alpha=0.3, axis="y")
    return finish(drawn, backend, output, "07_pump_energy_split.png")


FIGURES = (
    hydraulic_figure,
    transport_figure,
    temperature_chain_figure,
    energy_ledger_figure,
    fws_disturbance_figure,
    dt_convergence_figure,
    pump_energy_figure,
)


def main(argv):
    output = Path(argv[1]) if len(argv) > 1 else Path.cwd() / "figures" / "phase4"
    output.mkdir(parents=True, exist_ok=True)
    backend = load_backend()
    # The CJK face must be active while the Figure and its text objects are
    # created: a Text captures its font at construction, so wrapping only
    # `savefig` would silently render every Chinese label as tofu boxes.
    font = cjk_font(backend.mpl)
    with (
        backend.mpl.rc_context({"font.family": font, "axes.unicode_minus": False}),
        warnings.catch_warnings(record=True) as caught,
    ):
        warnings.simplefilter("always")
        written = [draw(backend, output) for draw in FIGURES]
    missing = sorted(
        {str(item.message) for item in caught if "missing from font" in str(item.message)}
    )
    if missing:
        raise SystemExit(
            f"{len(missing)} glyphs are missing from {font}; they would render as empty "
            "boxes. Replace them with characters the font covers:\n  "
            + "\n  ".join(missing)
        )
    print(f"\n{len(written)} figures written to {output}")


if __name__ == "__main__":
    main(sys.argv)
