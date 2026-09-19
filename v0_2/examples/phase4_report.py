"""Self-contained HTML evidence page for the frozen Phase 4 physical plant.

Same shape as the V0.1 benchmark page: one file, inline CSS, every figure embedded
as base64 so the page needs no sibling assets. Unlike the V0.1 page this one is not
locale-switched -- the figures are drawn bilingually, so the surrounding prose is
bilingual too.

Every number in the tables is read from `phase4_validation.evidence()` rather than
transcribed, so the page cannot disagree with the module that produced it.
`PHASE4_PHYSICAL_PLANT_REPORT.md` remains the authoritative record; this page is a
reading view of it.

Run from the repository root (writes `PHASE4_EVIDENCE.html` and regenerates the
figures under `figures/phase4/`):

    python -m v0_2.examples.phase4_report
"""

import base64
import html
import sys
from pathlib import Path

from v0_2.examples.phase4_figures import DISCLAIMER, render_all
from v0_2.examples.phase4_validation import evidence

# Identical to the V0.1 report stylesheet, so both pages read as one project.
STYLE = (
    "body{font:15px system-ui;max-width:1200px;margin:32px auto;color:#172033}"
    "table{border-collapse:collapse;width:100%}"
    "th,td{padding:8px;border:1px solid #ccd3df;text-align:left}"
    "th{background:#eef2f7}"
    ".note{background:#fff4d6;padding:14px;border-left:4px solid #c48600}"
    ".pass{color:#126c2e;font-weight:700}"
    ".fail{color:#b42318;font-weight:700;background:#fff1f0}"
    "code{background:#eef2f7;padding:2px 5px}"
    "img{max-width:100%;height:auto}"
)

GATE_STATUS = (
    "PHASE4_GATE_STATUS = PASS for the declared generic numerical fixture only. "
    "This is not an OEM-calibrated GB300 model, a safety claim, or an authorized "
    "controller."
)

LIMITS = (
    "The generic formulation is a single pump, common supply/return manifolds and "
    "quadratic path resistance; it is not a universal hydraulic graph solver. Fluid "
    "properties are constant: no viscosity or temperature feedback, compressibility, "
    "cavitation, two-phase behaviour, water hammer, FWS inventory, HX wall capacity, "
    "valve dynamics or actuator transients. Every fixture parameter stays "
    "ENGINEERING_ASSUMPTION / NUMERICAL_TEST_FIXTURE / UNVALIDATED until replaced by "
    "measured or vendor data. The pump H-Q-speed-efficiency map, VFD/motor "
    "efficiency, pipe and branch resistance, manifold geometry, CDU inventory, HX UA "
    "map, valve Cv and the whole FWS envelope remain CALIBRATION_REQUIRED."
)

# (figure file, Chinese heading, English heading, Chinese paragraph, English paragraph)
SECTIONS = (
    (
        "01_hydraulic_network.png",
        "图 1 水力网络：泵工作点与支路分流",
        "Figure 1 — Hydraulic network: pump operating point and branch split",
        ("泵曲线 <code>H = H0·speed² − Kpump·Q²</code> 与串联加并联的系统曲线在共用供回液压力"
        "节点上直接求交，支路流量由公共压降算出，不做任何事后归一化。星号为 2 支路 0.9× 的"
        "报告工作点；右图五个工况与水力表逐行对应，红色为 K×2 限制支路，受限制支路流量更低、"
        "与它并联的支路更高。"),
        ("The pump curve <code>H = H0·speed² − Kpump·Q²</code> intersects the "
        "series-plus-parallel system curve at the shared supply/return pressure junctions, "
        "and branch flows follow from the common pressure drop with no after-the-fact "
        "normalization. The star is the reported 2-branch 0.9× point; the bars mirror the "
        "five rows of the hydraulic table below, where the red K×2 restricted branch "
        "carries less flow and its parallel partner more."),
    ),
    (
        "07_pump_energy_split.png",
        "图 7 泵电能分解",
        "Figure 7 — Pump electrical energy split",
        ("泵电能按液压、泵内部、电机、VFD 分阶段分解，并给出入液与入环境两个去向。水力功只在"
        "被动阻力处转为热，不在泵上二次沉积。夹具的 <code>pump_efficiency=0.75</code> 与 "
        "<code>motor_efficiency=0.8</code> 使内部损失与电机损失在代数上相等，因此两根柱都是 "
        "17.469 J——这是所取效率的性质，不是重复计账。"),
        ("Pump electrical energy split by stage and by destination. Hydraulic work becomes "
        "heat only at passive resistances, never a second time at the pump. The fixture's "
        "<code>pump_efficiency=0.75</code> and <code>motor_efficiency=0.8</code> make the "
        "internal and motor losses algebraically equal, so both bars read 17.469 J; that is "
        "a property of the chosen efficiencies, not a duplicated posting."),
    ),
    (
        "02_transport_convergence.png",
        "图 2 冷却液输运：对解析解的 dt 收敛",
        "Figure 2 — Coolant transport: dt convergence to the analytic reference",
        ("一单元有限体积输运的出口温度随 dt 细化逼近解析解 "
        "<code>T(t) = Tin + (T0 − Tin)·e^(−m_dot·t/M)</code>，末端误差 "
        "0.0724 → 0.0365 → 0.0183 K，呈一阶收敛。零流量时单元保留其质量、焓与温度。"),
        ("The one-cell finite-volume outlet approaches the analytic reference "
        "<code>T(t) = Tin + (T0 − Tin)·e^(−m_dot·t/M)</code> as dt refines, with end-point "
        "error falling 0.0724 → 0.0365 → 0.0183 K at first order. At zero flow a cell "
        "retains its mass, enthalpy and temperature."),
    ),
    (
        "05_fws_disturbance.png",
        "图 5 FWS 扰动响应",
        "Figure 5 — FWS disturbance response",
        ("5 s 时施加 FWS 扰动，10 s 时读数。CDU 二次侧有 2 kg 有限存量，因此渐变而不跳变。"
        "升温的 FWS 与降低的 FWS 流量都削弱本夹具的排热能力：一次侧入口 290→294 K 使供液升至 "
        "299.540 K、HX 二次侧出口降至 511.9 W；一次侧流量 0.4→0.28 kg/s 则给出 299.378 K 与 "
        "856.1 W。一次侧流体不进入二次侧质量账本。"),
        ("An FWS disturbance is applied at 5 s and read at 10 s. The CDU holds a finite 2 kg "
        "inventory, so it drifts rather than stepping. Warmer FWS and reduced FWS flow both "
        "weaken heat removal in this fixture: a 290→294 K primary inlet raises the supply to "
        "299.540 K and drops HX secondary export to 511.9 W, while 0.4→0.28 kg/s gives "
        "299.378 K and 856.1 W. No primary fluid enters the secondary mass ledger."),
    ),
    (
        "03_temperature_chain.png",
        "图 3 耦合温度链",
        "Figure 3 — Coupled temperature chain",
        ("相对 CDU 供液的温升：裸片 2.801 K，封装 0.677 K，冷板 0.433 K，局部冷却液 0.394 K，"
        "裸片承担几乎全部梯度。绝对温度图上，冷 FWS 使供液在 5 s 内下移 0.413 K 至 299.587 K；"
        "回液看似持平，是因为局部冷却液温升几乎正好抵消了该下移。"),
        ("Rise above the CDU supply: die 2.801 K, package 0.677 K, cold plate 0.433 K, local "
        "coolant 0.394 K, so the die carries nearly the whole gradient. On the absolute axis "
        "the cold FWS pulls the supply down 0.413 K to 299.587 K over 5 s, and the return "
        "looks flat because the local coolant rise almost exactly offsets that drift."),
    ),
    (
        "04_energy_ledger.png",
        "图 4 全回路能量账与残差",
        "Figure 4 — Full-loop energy ledger and residual",
        ("全回路能量方程 <code>ΔE = E_IT + E_泵入液 − E_空气 − E_HX</code>。本夹具故意使用冷 "
        "FWS，故 IT 加泵热小于 HX 导出、储能变化为负——这是物理瞬态，不是能量不守恒。图中为 "
        "2 支路 dt=0.2 s 单次运行（25 步），其单步残差率最大 2.19e-9 W；十二组运行的全局最大值 "
        "1.31e-8 W 出自 4 支路 dt=0.05 s，两者范围不同而非不一致。泵电能单独报告，不整体二次计入。"),
        ("The full-loop equation <code>ΔE = E_IT + E_pump_to_liquid − E_air − E_HX</code>. This "
        "fixture deliberately runs a cold FWS, so IT plus pump heat is smaller than HX export "
        "and the stored change is negative: a physical transient, not an energy-balance "
        "violation. The chart is the single 2-branch dt=0.2 s run (25 steps) with a largest "
        "per-step residual rate of 2.19e-9 W; the global maximum 1.31e-8 W comes from the "
        "4-branch dt=0.05 s case. The two differ in scope, not in value. Pump electrical "
        "consumption is reported separately, never added in full a second time."),
    ),
    (
        "06_dt_convergence.png",
        "图 6 网格收敛：四个场景",
        "Figure 6 — Mesh (dt) convergence across all four scenarios",
        ("左：2 支路裸片轨迹在三套网格下重合，峰值 302.387748 / 302.395106 / 302.398817 K，"
        "因此差异必须以数字而非曲线间距表述。右：各场景相邻差异与冻结容差之比（取十个受检指标中"
        "最差者），全部远低于 1。流量、压力与泵能量的网格差异恒为零，因为每个区间内水力映射与"
        "保持的转速不变。"),
        ("Left: the two-branch die trajectory coincides across the three meshes, peaking at "
        "302.387748 / 302.395106 / 302.398817 K, so the separation has to be stated as "
        "numbers rather than read off the lines. Right: each scenario's worst "
        "metric-to-tolerance ratio across the ten checked metrics, all far below 1. Flow, "
        "pressure and pump energy have exactly zero mesh error because the hydraulic map and "
        "held speed are static within each interval."),
    ),
)


def _f(value, digits=6):
    return f"{float(value):.{digits}f}"


def _e(value):
    return f"{float(value):.2e}"


def _table(headers, rows):
    head = "".join(f"<th>{html.escape(item)}</th>" for item in headers)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def hydraulic_table(reported):
    rows = []
    for row in reported:
        flows = ", ".join(_f(flow) for flow in row["branch_flows_kg_s"])
        rows.append(
            "<tr>"
            f"<td>{row['branches']}</td>"
            f"<td>{row['branch_0_multiplier']:g}</td>"
            f"<td>{row['speed']:g}</td>"
            f"<td>{_f(row['total_flow_kg_s'])}</td>"
            f"<td>{_f(row['pump_dp_pa'], 4)}</td>"
            f"<td>{flows}</td>"
            f"<td>{_f(row['manifold_dp_pa'], 4)}</td>"
            f"<td>{row['iterations']}</td>"
            f"<td>{_e(row['residual_norm'])}</td>"
            "</tr>"
        )
    return _table(
        ("支路 Branches", "0 号 K 倍数 K mult.", "转速 Speed", "总流量 Total kg/s",
         "泵 ΔP Pump Pa", "支路流量 Branch kg/s", "总管 ΔP Manifold Pa",
         "迭代 Iter", "残差范数 Residual"),
        rows,
    )


def transport_table(reported):
    rows = []
    for row in reported:
        rows.append(
            "<tr>"
            f"<td>{row['dt_s']:g}</td>"
            f"<td>{_f(row['outlet_k'], 6)}</td>"
            f"<td>{_f(row['outlet_h_j_kg'])}</td>"
            f"<td>{_f(row['stored_change_j'])}</td>"
            f"<td>{_f(row['analytic_k'], 6)}</td>"
            f"<td>{_f(row['error_k'], 6)}</td>"
            "</tr>"
        )
    return _table(
        ("dt s", "出口 Outlet K", "出口焓 Outlet h J/kg", "储能变化 Stored J",
         "解析 Analytic K", "绝对误差 Abs error K"),
        rows,
    )


def fws_table(reported):
    labels = (
        ("base", "基线 Baseline 290 K / 0.4 kg/s"),
        ("warm_290_to_294_k", "入口 290→294 K Inlet"),
        ("flow_0.4_to_0.28_kg_s", "流量 0.4→0.28 kg/s Flow"),
    )
    rows = []
    for key, label in labels:
        item = reported[key]
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{_f(item['cdu_k'], 6)}</td>"
            f"<td>{_f(item['hx_final_w'], 6)}</td>"
            "</tr>"
        )
    return _table(("FWS 条件 Condition", "CDU 供液 Supply K", "HX 二次侧出口 Export W"), rows)


def ledger_table(metrics):
    entries = (
        ("IT 注入 IT source", "source_j", _f, "J"),
        ("泵电能 Pump electrical", "pump_electrical_j", _f, "J"),
        ("泵水力 Pump hydraulic", "pump_hydraulic_j", _f, "J"),
        ("泵热入液 Pump to liquid", "pump_heat_liquid_j", _f, "J"),
        ("空气排出 Air", "air_j", _f, "J"),
        ("HX 排出 HX export", "hx_j", _f, "J"),
        ("储能变化 Stored change", "stored_j", _f, "J"),
        ("有符号残差 Signed residual", "signed_energy_residual_j", _e, "J"),
        ("残差和 Sum abs residual", "sum_abs_energy_residual_j", _e, "J"),
    )
    rows = [
        f"<tr><td>{html.escape(label)}</td><td>{fmt(metrics[key])}</td><td>{unit}</td></tr>"
        for label, key, fmt, unit in entries
    ]
    return _table(("项 Item", "值 Value", "单位 Unit"), rows)


def convergence_table(reported):
    rows = []
    for name, report in reported.items():
        peaks = " / ".join(_f(item["peak_k"], 6) for item in report["metrics"])
        adjacent = report["adjacent_differences"]
        errors = " / ".join(_f(item["peak_k"], 6) for item in adjacent)
        status_class = "pass" if report["status"] == "PASS" else "fail"
        rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{peaks}</td>"
            f"<td>{errors}</td>"
            f"<td class='{status_class}'>{html.escape(report['status'])}</td>"
            "</tr>"
        )
    return _table(
        ("场景 Scenario", "峰值 at 0.2 / 0.1 / 0.05 s (K)", "相邻峰值误差 Adjacent (K)", "门禁"),
        rows,
    )


def page(figures_dir):
    reported = evidence()
    two_branch = reported["convergence"]["two_branch"]
    metrics = two_branch["metrics"][0]

    parts = [
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
        "<title>C2C-DTB V0.2 Phase 4 证据页 / Phase 4 evidence</title>",
        f"<style>{STYLE}</style></head><body>",
        ("<h1>C2C-DTB V0.2 Phase 4 物理装置验证<br>"
        "<span style='font-size:0.72em;font-weight:400'>V0.2 Phase 4 physical-plant "
        "verification</span></h1>"),
        (f"<p class='note'>{html.escape(GATE_STATUS)}<br>"
        f"{html.escape(DISCLAIMER)}</p>"),
        ("<p>本页是 <code>PHASE4_PHYSICAL_PLANT_REPORT.md</code> 的阅读视图；表格数字与图片均由 "
        "证据模块 <code>v0_2.examples.phase4_validation</code> 生成，非手工转录。复现："
        "<code>python -m v0_2.examples.phase4_validation</code>；重绘本页："
        "<code>python -m v0_2.examples.phase4_report</code>。</p>"),
        ("<p>This page is a reading view of "
        "<code>PHASE4_PHYSICAL_PLANT_REPORT.md</code> and introduces no new claims. Every "
        "table value and figure is produced from the evidence module "
        "<code>v0_2.examples.phase4_validation</code> rather than transcribed by hand. "
        "Reproduce with <code>python -m v0_2.examples.phase4_validation</code>, or rebuild "
        "this page with <code>python -m v0_2.examples.phase4_report</code>.</p>"),
    ]

    for name, zh_title, en_title, zh_text, en_text in SECTIONS:
        encoded = base64.b64encode((figures_dir / name).read_bytes()).decode("ascii")
        parts.append(f"<h2>{html.escape(zh_title)}<br>"
                     f"<span style='font-size:0.8em;font-weight:400'>"
                     f"{html.escape(en_title)}</span></h2>")
        parts.append(f"<p>{zh_text}</p><p>{en_text}</p>")
        parts.append(
            f"<img alt='{html.escape(zh_title)} / {html.escape(en_title)}' "
            f"src='data:image/png;base64,{encoded}'>"
        )

    tables = (
        ("水力工作点 / Hydraulic operating points", hydraulic_table(reported["hydraulic"])),
        ("一单元输运 / One-cell transport", transport_table(reported["transport"])),
        ("FWS 扰动（10 s 读数）/ FWS disturbance, read at 10 s", fws_table(reported["fws"])),
        (
            "全回路能量账本：2 支路 5 s，dt 0.2 s / Full-loop energy ledger",
            ledger_table(metrics),
        ),
        ("网格收敛：四场景 / Mesh convergence, four scenarios", convergence_table(
            reported["convergence"]
        )),
    )
    for title, table in tables:
        parts.append(f"<h2>{html.escape(title)}</h2>{table}")

    parts.append("<h2>模型边界 / Model boundaries</h2>")
    parts.append(f"<p class='note'>{html.escape(LIMITS)}</p>")
    parts.append("</body></html>")
    return "".join(parts)


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    figures_dir = root / "figures" / "phase4"
    figures_dir.mkdir(parents=True, exist_ok=True)
    render_all(figures_dir)
    target = root / "PHASE4_EVIDENCE.html"
    target.write_text(page(figures_dir), encoding="utf-8")
    print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv)
