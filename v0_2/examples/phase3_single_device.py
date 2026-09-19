import json

from v0_2.thermal.fixtures import insulated
from v0_2.thermal.harness import run
from v0_2.thermal.integrator import Method


def main():
    print(
        json.dumps(
            {m.value: run(insulated(), 10_000_000_000, 100_000_000, m).metrics() for m in Method},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
