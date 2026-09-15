from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from c2c.i18n import translate

_CJK_FONT_CANDIDATES = (
    "Noto Sans CJK SC",
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
)


def _font_family(locale: str) -> str:
    if locale != "zh-CN":
        return "DejaVu Sans"
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in _CJK_FONT_CANDIDATES:
        if candidate in installed:
            return candidate
    raise RuntimeError(
        "Chinese plot output requires a CJK font; install Noto Sans CJK, "
        "Microsoft YaHei, SimHei, or WenQuanYi Zen Hei"
    )


def comparison_plot(
    frame, output: str | Path, locale: str = "en", step_times: tuple[float, ...] = (300, 750)
) -> Path:
    output = Path(output)
    with mpl.rc_context({"font.family": _font_family(locale), "axes.unicode_minus": False}):
        fig = Figure(figsize=(14, 12))
        FigureCanvasAgg(fig)
        axes = fig.subplots(3, 2, sharex=True)
        colors = {"feedback_only": "#3766a3", "guarded_feedforward": "#d26a2e"}
        series = (
            "gpu_power_kw",
            "gpu_temperature_c",
            "secondary_supply_temp_c",
            "secondary_return_temp_c",
            "secondary_flow_m3h",
            "pump_power_kw",
        )
        for axis, column in zip(axes.flat, series, strict=True):
            for name, case in frame.groupby("case", sort=False):
                axis.plot(
                    case.timestamp_s,
                    case[column],
                    label=translate(f"case.{name}", locale),
                    color=colors[name],
                    linewidth=1.6,
                )
            for step_s in step_times:
                axis.axvline(step_s, color="#777", linestyle="--", linewidth=0.8)
            axis.set_ylabel(translate(f"plot.{column}", locale))
            axis.grid(alpha=0.25)
        axes[-1, 0].set_xlabel(translate("plot.time", locale))
        axes[-1, 1].set_xlabel(translate("plot.time", locale))
        axes[0, 0].legend(loc="best")
        fig.suptitle(translate("plot.title", locale))
        fig.tight_layout()
        fig.savefig(output, dpi=150)
    return output
