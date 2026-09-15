from pathlib import Path

import yaml

from c2c.core.provenance import ParameterRecord, values_only
from c2c.simulation.validation import ScenarioValidationError, validate_scenario


def _validate_provenance_records(value: object, path: str = "scenario") -> None:
    if isinstance(value, dict):
        if "value" in value:
            try:
                ParameterRecord.model_validate(value)
            except ValueError as exc:
                raise ScenarioValidationError(
                    f"Invalid provenance record at {path}: {exc}"
                ) from exc
            return
        for key, item in value.items():
            _validate_provenance_records(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_provenance_records(item, f"{path}[{index}]")


def load_scenario(path: str | Path) -> tuple[dict, dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ScenarioValidationError("scenario root must be a mapping")
    _validate_provenance_records(raw)
    config = values_only(raw)
    validate_scenario(config)
    return raw, config
