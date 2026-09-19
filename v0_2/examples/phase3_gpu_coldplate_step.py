import json

from v0_2.thermal.fixtures import gpu_chain, with_power
from v0_2.thermal.harness import BoundaryEvent, convergence, run


def main():
    f = gpu_chain(power=30.0)
    high = with_power(f, 120.0)
    event = BoundaryEvent(20_000_000_000, high.sources, f.boundaries, f.flows)
    runs = [
        run(f, 100_000_000_000, dt, events=(event,))
        for dt in (200_000_000, 100_000_000, 50_000_000)
    ]
    print(json.dumps(convergence(runs), indent=2))


if __name__ == "__main__":
    main()
