from pathlib import Path

import matplotlib as mpl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from c2c.i18n import translate
from c2c.reports.plots import _font_family

# Threshold crossings are display conventions, not sensor detection times.
EVENTS = {
    "power": ("gpu_power_kw", 1.0),
    "pump": ("pump_speed_pct", 2.0),
    "valve": ("valve_position_pct", 2.0),
    "temperature": ("plc_measured_supply_temp_c", 0.1),
    "pressure": ("plc_measured_dp_kpa", 0.2),
}


def response_events(frame, config: dict) -> dict:
    step = float(config["workload"]["phases"][1]["start_s"])
    phases = config["workload"]["phases"]
    end = float(phases[2]["start_s"] if len(phases) > 2 else config["time"]["duration_s"])
    result = {
        "step_s": step,
        "end_s": end,
        "baseline_window_s": [max(0, step - 60), step],
        "thresholds": {
            key: {"column": field, "absolute_change": limit}
            for key, (field, limit) in EVENTS.items()
        },
        "cases": {},
    }
    for name, case in frame.groupby("case", sort=False):
        pre = case[(case.timestamp_s >= max(0, step - 60)) & (case.timestamp_s < step)]
        after = case[(case.timestamp_s >= step) & (case.timestamp_s < end)]
        events = {}
        for key, (column, threshold) in EVENTS.items():
            crossed = after[(after[column] - pre[column].mean()).abs() >= threshold]
            events[key] = None if crossed.empty else float(crossed.timestamp_s.iloc[0] - step)
        refreshed = after[after.lci_intent_timestamp_s >= step]
        events["intent"] = None if refreshed.empty else float(refreshed.timestamp_s.iloc[0] - step)
        result["cases"][name] = events
    return result


def response_timeline(frame, config: dict, output: str | Path, locale: str = "en") -> Path:
    events = response_events(frame, config)
    step, end = events["step_s"], events["end_s"]
    specs = (
        ("power", [("gpu_power_kw", "power", "-")]),
        (
            "temp_target",
            [
                ("accepted_temperature_setpoint_c", "accepted", ":"),
                ("temperature_setpoint_c", "actual", "-"),
            ],
        ),
        ("dp_target", [("accepted_dp_kpa", "accepted", "-")]),
        ("pump", [("pump_speed_pct", "pump", "-")]),
        ("valve", [("valve_position_pct", "valve", "-")]),
        ("temperature", [("plc_measured_supply_temp_c", "temperature", "-")]),
        ("pressure", [("plc_measured_dp_kpa", "pressure", "-")]),
    )
    with mpl.rc_context({"font.family": _font_family(locale), "axes.unicode_minus": False}):
        fig = Figure(figsize=(14, 17), layout="constrained")
        FigureCanvasAgg(fig)
        axes = fig.subplots(len(specs), 2, sharex=True, sharey="row")
        for col, name in enumerate(("feedback_only", "guarded_feedforward")):
            case = frame[frame.case == name]
            pre = case[(case.timestamp_s >= max(0, step - 60)) & (case.timestamp_s < step)]
            visible = case[
                (case.timestamp_s >= max(0, step - 30)) & (case.timestamp_s < min(end, step + 181))
            ]
            color = ("#3766a3", "#d26a2e")[col]
            for row, (key, curves) in enumerate(specs):
                ax = axes[row, col]
                for field, label, style in curves:
                    y = visible[field]
                    if key in {"temperature", "pressure"}:
                        y = y - pre[field].mean()
                    ax.plot(
                        visible.timestamp_s - step,
                        y,
                        linestyle=style,
                        color=color,
                        label=translate(f"timeline.{label}", locale),
                    )
                ax.axvline(0, color="#555", linestyle="--", linewidth=0.8)
                if key in {"temperature", "pressure"}:
                    for sign in (-1, 1):
                        ax.axhline(sign * EVENTS[key][1], color="#999", linestyle=":")
                delay = events["cases"][name].get(key)
                if delay is not None and delay <= visible.timestamp_s.max() - step:
                    ax.axvline(delay, color="#7753a0", linestyle=":")
                    ax.text(
                        0.98,
                        0.92,
                        f"{delay:g} s",
                        transform=ax.transAxes,
                        ha="right",
                        va="top",
                        fontsize=9,
                        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
                    )
                ax.set_ylabel(translate(f"timeline.axis_{key}", locale))
                ax.grid(alpha=0.2)
                if row == 1:
                    ax.legend(fontsize=8)
            axes[0, col].set_title(translate(f"case.{name}", locale))
            axes[-1, col].set_xlabel(translate("timeline.time", locale))
        fig.suptitle(translate("timeline.title", locale))
        output = Path(output)
        fig.savefig(output, dpi=140)
    return output
