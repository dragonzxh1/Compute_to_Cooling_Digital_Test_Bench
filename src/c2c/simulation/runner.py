import argparse
import base64
import html
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

from c2c.i18n import SUPPORTED_LOCALES, normalize_locale, translate
from c2c.reports.metrics import benchmark_summary
from c2c.reports.plots import comparison_plot
from c2c.simulation.engine import run_benchmark
from c2c.simulation.scenario import load_scenario


def _git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _shown(value: object, metric: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if (
            metric
            in {
                "controller_oscillation_index",
                "controller_valve_oscillation_index",
                "valve_oscillation",
            }
            and 0 < value < 0.0001
        ):
            return "< 0.0001"
        return f"{value:.4g}"
    return str(value)


def _html_report(summary: dict, image_path: Path, step_s: float, locale: str) -> str:
    image = base64.b64encode(image_path.read_bytes()).decode("ascii")
    rows = []
    check_rows = []
    for case, metrics in summary["cases"].items():
        case_status = metrics["threshold_status"].lower()
        check_rows.append(
            f"<tr><td>{html.escape(translate(f'case.{case}', locale))}</td>"
            f"<td colspan='3'>{html.escape(translate('report.overall', locale))}</td>"
            f"<td>{html.escape(translate(f'report.{case_status}', locale))}</td></tr>"
        )
        for metric, value in metrics.items():
            if metric in {"threshold_checks", "threshold_status"}:
                continue
            rows.append(
                "<tr>"
                f"<td>{html.escape(translate(f'case.{case}', locale))}</td>"
                f"<td>{html.escape(translate(f'metric.{metric}', locale))}</td>"
                f"<td>{html.escape(_shown(value, metric))}</td>"
                "</tr>"
            )
        for check in metrics["threshold_checks"]:
            status_key = "report.pass" if check["passed"] else "report.fail"
            status_class = "pass" if check["passed"] else "fail"
            check_rows.append(
                "<tr>"
                f"<td>{html.escape(translate(f'case.{case}', locale))}</td>"
                f"<td>{html.escape(check['label'])}</td>"
                f"<td>{html.escape(_shown(check['actual'], check['key']))} "
                f"{html.escape(check['unit'])}</td>"
                f"<td>{html.escape(check['comparison'])} {check['limit']:.4g} "
                f"{html.escape(check['unit'])}</td>"
                f"<td class='{status_class}'>{html.escape(translate(status_key, locale))}</td>"
                "</tr>"
            )
    language = "zh-CN" if locale == "zh-CN" else "en"
    return f"""<!doctype html><html lang='{language}'><head><meta charset='utf-8'><title>{html.escape(translate("report.page_title", locale))}</title>
<style>body{{font:15px system-ui;max-width:1200px;margin:32px auto;color:#172033}}table{{border-collapse:collapse;width:100%}}th,td{{padding:8px;border:1px solid #ccd3df;text-align:left}}th{{background:#eef2f7}}.note{{background:#fff4d6;padding:14px;border-left:4px solid #c48600}}.pass{{color:#126c2e;font-weight:700}}.fail{{color:#b42318;font-weight:700;background:#fff1f0}}img{{max-width:100%;height:auto}}</style></head><body>
<h1>{html.escape(translate("report.title", locale))}</h1><p class='note'>{html.escape(summary["claims"])}</p>
<p>{html.escape(translate("report.explanation", locale, step_s=step_s))}</p>
<img alt='{html.escape(translate("report.plot_alt", locale))}' src='data:image/png;base64,{image}'>
<h2>{html.escape(translate("report.threshold_checks", locale))}</h2><table><thead><tr><th>{html.escape(translate("report.case", locale))}</th><th>{html.escape(translate("report.metric", locale))}</th><th>{html.escape(translate("report.value", locale))}</th><th>{html.escape(translate("report.limit", locale))}</th><th>{html.escape(translate("report.status", locale))}</th></tr></thead><tbody>{"".join(check_rows)}</tbody></table>
<h2>{html.escape(translate("report.kpis", locale))}</h2><table><thead><tr><th>{html.escape(translate("report.case", locale))}</th><th>{html.escape(translate("report.metric", locale))}</th><th>{html.escape(translate("report.value", locale))}</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<h2>{html.escape(translate("report.interpretation_limits", locale))}</h2><p>{html.escape(translate("report.limits_text", locale))}</p>
</body></html>"""


def _default_config_path() -> Path:
    installed = Path(sys.prefix) / "configs" / "scenarios" / "workload_step.yaml"
    if installed.is_file():
        return installed
    return Path(__file__).resolve().parents[3] / "configs" / "scenarios" / "workload_step.yaml"


def run(
    config_path: str | Path | None = None,
    output_root: str | Path = "results",
    locale: str = "en",
) -> Path:
    locale = normalize_locale(locale)
    raw, config = load_scenario(_default_config_path() if config_path is None else config_path)
    generated = datetime.now(UTC)
    run_id = f"{config['name']}-{generated.strftime('%Y%m%dT%H%M%S%fZ')}"
    output = Path(output_root) / run_id
    output.mkdir(parents=True, exist_ok=False)
    frame = run_benchmark(config)
    summary = benchmark_summary(frame, config, locale)
    (output / "config.yaml").write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "generated_at": generated.isoformat(),
        "seed": config["seed"],
        "python": platform.python_version(),
        "git_revision": _git_revision(),
        "timebase_s": config["time"]["dt_s"],
        "model": "C2C-DTB V0.1 reduced-order deterministic model",
        "locale": locale,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    frame.to_csv(output / "timeseries.csv", index=False)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    step_times = tuple(float(phase["start_s"]) for phase in config["workload"]["phases"][1:])
    plot_path = comparison_plot(frame, output / "comparison.png", locale, step_times)
    step_s = step_times[0] if step_times else 0.0
    (output / "report.html").write_text(
        _html_report(summary, plot_path, step_s, locale), encoding="utf-8"
    )
    return output.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the C2C-DTB V0.1 comparison benchmark")
    parser.add_argument("config", nargs="?", default=None)
    parser.add_argument("--output-root", default="results")
    parser.add_argument("--locale", choices=SUPPORTED_LOCALES, default="en")
    args = parser.parse_args()
    print(run(args.config, args.output_root, args.locale))


if __name__ == "__main__":
    main()
