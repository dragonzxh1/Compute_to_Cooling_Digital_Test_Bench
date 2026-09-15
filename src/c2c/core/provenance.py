from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class SourceType(StrEnum):
    MEASURED = "MEASURED"
    OEM = "OEM"
    NVIDIA = "NVIDIA"
    LITERATURE = "LITERATURE"
    ASSUMED = "ASSUMED"
    CALIBRATED = "CALIBRATED"


class ParameterRecord(BaseModel):
    value: float | int | str
    unit: str
    source_type: SourceType
    source: str
    date: date
    confidence: str
    notes: str


def values_only(value: Any) -> Any:
    """Recursively unwrap provenance records while leaving ordinary mappings intact."""
    if isinstance(value, dict):
        required = {"value", "unit", "source_type", "source", "date", "confidence", "notes"}
        if required.issubset(value):
            return value["value"]
        return {key: values_only(item) for key, item in value.items()}
    if isinstance(value, list):
        return [values_only(item) for item in value]
    return value
