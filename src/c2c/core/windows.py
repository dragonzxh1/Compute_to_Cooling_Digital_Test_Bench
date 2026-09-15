def benchmark_windows(config: dict) -> tuple[tuple[float, float], ...]:
    """Half-open pre-step, high-load and late high-load reporting windows."""
    phases = config["workload"]["phases"]
    step = float(phases[1]["start_s"])
    end = float(phases[2]["start_s"]) if len(phases) > 2 else float(config["time"]["duration_s"])
    return (
        (max(0.0, step - 60), step),
        (step, end),
        (max(step, end - min(100.0, (end - step) / 2)), end),
    )
