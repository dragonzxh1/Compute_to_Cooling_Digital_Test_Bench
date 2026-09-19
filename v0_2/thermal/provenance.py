from dataclasses import dataclass
from datetime import date as Date

from .validity import finite, require


@dataclass(frozen=True)
class ParameterRecord:
    name: str
    value: float
    unit: str
    source_type: str
    source_ref: str
    confidence: float
    date: str
    valid_range: tuple[float, float]
    calibration_status: str

    def __post_init__(self):
        require(bool(self.name and self.unit and self.source_ref), "PROVENANCE", self.name)
        finite(self.value, self.name)
        finite(self.confidence, "confidence")
        require(0 <= self.confidence <= 1, "PROVENANCE", "confidence")
        require(
            self.source_type
            in {
                "OFFICIAL",
                "DATASHEET",
                "LITERATURE",
                "ENGINEERING_ASSUMPTION",
                "MEASURED",
                "CALIBRATED",
            },
            "PROVENANCE",
            "source_type",
        )
        require(
            self.calibration_status
            in {"UNVALIDATED", "CALIBRATION_REQUIRED", "CALIBRATED", "VALIDATED"},
            "PROVENANCE",
            "calibration_status",
        )
        require(
            type(self.valid_range) is tuple and len(self.valid_range) == 2,
            "PROVENANCE",
            "immutable valid_range",
        )
        for value in self.valid_range:
            finite(value, "valid_range")
        require(
            self.valid_range[0] <= self.value <= self.valid_range[1],
            "PROVENANCE",
            "value outside declared range",
        )
        Date.fromisoformat(self.date)

    def si(self, unit):
        require(self.unit == unit, "UNIT_MISMATCH", f"{self.name}: expected {unit}")
        return self.value


def fixture_parameter(name, value, unit, valid_range=None):
    """Explicit NUMERICAL_TEST_FIXTURE provenance, never hardware validation."""
    return ParameterRecord(
        name,
        value,
        unit,
        "ENGINEERING_ASSUMPTION",
        "NUMERICAL_TEST_FIXTURE: phase3 analytic/generic examples",
        0.0,
        "2026-09-18",
        valid_range or (value, value),
        "UNVALIDATED",
    )
