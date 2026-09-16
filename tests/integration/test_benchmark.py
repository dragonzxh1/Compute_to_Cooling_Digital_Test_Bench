from copy import deepcopy
from pathlib import Path

import pytest

from c2c.reports.metrics import _check, benchmark_summary
from c2c.simulation.engine import run_benchmark
from c2c.simulation.runner import run
from c2c.simulation.scenario import load_scenario

CONFIG = Path("configs/scenarios/workload_step.yaml")


def test_benchmark_is_reproducible_and_feedforward_is_earlier():
    _, config = load_scenario(CONFIG)
    first = run_benchmark(config)
    second = run_benchmark(config)
    assert first.equals(second)
    summary = benchmark_summary(first, config)
    feedback = summary["cases"]["feedback_only"]["controller_response_delay_s"]
    feedforward = summary["cases"]["guarded_feedforward"]["controller_response_delay_s"]
    assert feedforward is not None and feedback is not None
    assert feedforward < feedback
    assert set(first.case.unique()) == {"feedback_only", "guarded_feedforward"}
    assert (
        first[["gpu_temperature_c", "secondary_flow_m3h", "heat_rejected_kw"]].notna().all().all()
    )
    assert summary["cases"]["feedback_only"]["threshold_status"] == "PASS"
    ff = summary["cases"]["guarded_feedforward"]
    assert ff["threshold_status"] == "PASS"
    assert ff["max_accepted_target_deviation_k"] > 3
    assert ff["setpoint_response_delay_s"] > 0


def test_runner_writes_required_artifacts(tmp_path):
    output = run(CONFIG, tmp_path)
    for name in [
        "config.yaml",
        "metadata.json",
        "timeseries.csv",
        "summary.json",
        "report.html",
        "comparison.png",
        "response_timeline.png",
        "response_events.json",
    ]:
        assert (output / name).is_file()
    assert "Generic assumed equipment" in (output / "report.html").read_text(encoding="utf-8")


def test_runner_uses_packaged_or_repository_default_config(tmp_path):
    output = run(None, tmp_path)
    assert (output / "summary.json").is_file()


def test_runner_writes_localized_chinese_report(tmp_path):
    output = run(CONFIG, tmp_path, locale="zh-CN")
    report = (output / "report.html").read_text(encoding="utf-8")
    assert "阈值检查" in report
    assert "结果解释边界" in report
    assert "相对最终接受目标的最大偏差" in report
    assert "基准测试对比图" in report
    assert "控制响应时间线" in report
    assert "不是传感器感知延迟" in report
    assert "metric." not in report
    assert "peak_gpu_temperature_c" not in report


def test_metrics_follow_configured_workload_phase_times():
    _, config = load_scenario(CONFIG)
    shifted = deepcopy(config)
    shifted["time"]["duration_s"] = 700
    shifted["workload"]["phases"][1]["start_s"] = 200
    shifted["workload"]["phases"][2]["start_s"] = 500
    summary = benchmark_summary(run_benchmark(shifted), shifted)
    feedback = summary["cases"]["feedback_only"]["controller_response_delay_s"]
    feedforward = summary["cases"]["guarded_feedforward"]["controller_response_delay_s"]
    assert feedback is not None and feedback > 0
    assert feedforward is not None and 0 < feedforward < feedback
    assert summary["cases"]["guarded_feedforward"]["setpoint_response_delay_s"] > 0


def test_threshold_check_reports_a_real_failure():
    _, config = load_scenario(CONFIG)
    strict = deepcopy(config)
    strict["reporting"]["limits"]["max_supply_deviation_k"] = 0.1
    summary = benchmark_summary(run_benchmark(strict), strict)
    assert summary["cases"]["feedback_only"]["threshold_status"] == "FAIL"
    check = next(
        item
        for item in summary["cases"]["feedback_only"]["threshold_checks"]
        if item["key"] == "supply_deviation"
    )
    assert check["passed"] is False


@pytest.mark.parametrize(
    ("comparison", "actual", "expected"),
    [("<", 90, False), ("<=", 90, True), (">=", 90, True), (">=", 89, False)],
)
def test_threshold_comparison_boundaries(comparison, actual, expected):
    assert _check("gpu_temperature", actual, 90, comparison, "°C", "en")["passed"] is expected
