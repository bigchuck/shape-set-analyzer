from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Iterator

from shape_set_analyzer.models.imported_shape import ImportedShape

@dataclass
class AnalysisSection:
    """Collected observations for one area of set analysis."""

    observations: dict[str, Any] = field(default_factory=dict)
    classifications: dict[str, Any] = field(default_factory=dict)


@dataclass
class SetAnalysisMetadata:
    """State shared by all sections of a set analysis."""

    files_analyzed: int = 0
    analyzed_at: str | None = None


@dataclass
class SetAnalysis:
    """Sectioned analysis accumulated while consuming a shape set."""

    parameters: AnalysisSection = field(default_factory=AnalysisSection)
    statistics: AnalysisSection = field(default_factory=AnalysisSection)
    geometry: AnalysisSection = field(default_factory=AnalysisSection)
    metadata: SetAnalysisMetadata = field(default_factory=SetAnalysisMetadata)

def update_parameter_summary(
    analysis: SetAnalysis,
    shape: ImportedShape,
) -> None:
    """Add one shape's procedure observations to a set analysis."""
    analysis.metadata.files_analyzed += 1

    _record_observation(
        analysis.parameters,
        "procedure.method",
        shape.procedure.method,
        shape.source_file.as_posix(),
    )

    for path, value in _walk_parameter_values(
        shape.procedure.parameters,
        prefix="procedure.parameters",
    ):
        _record_observation(
            analysis.parameters,
            path,
            value,
            shape.source_file.as_posix(),
        )


def _walk_parameter_values(
    value: Any,
    *,
    prefix: str,
) -> Iterator[tuple[str, Any]]:
    """Yield leaf parameter paths while preserving lists as whole values."""
    if isinstance(value, dict) and value:
        for key, child_value in value.items():
            yield from _walk_parameter_values(
                child_value,
                prefix=f"{prefix}.{key}",
            )
        return

    yield prefix, value


def _record_observation(
    section: AnalysisSection,
    path: str,
    value: Any,
    source_file: str,
) -> None:
    """Record one observed value without classifying it."""
    observation = section.observations.setdefault(
        path,
        {
            "seen_in_files": 0,
            "types": {},
            "values": {},
        },
    )

    observation["seen_in_files"] += 1

    type_name = _value_type_name(value)
    observation["types"][type_name] = (
        observation["types"].get(type_name, 0) + 1
    )

    value_key = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    )

    value_observation = observation["values"].setdefault(
        value_key,
        {
            "value": deepcopy(value),
            "count": 0,
            "example_file": source_file,
        },
    )
    value_observation["count"] += 1


def _value_type_name(value: Any) -> str:
    """Return a JSON-oriented type name for an observed value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"

    return type(value).__name__

def classify_parameter_summary(
    analysis: SetAnalysis,
) -> None:
    """Classify all collected parameter observations."""

    analysis.parameters.classifications.clear()

    expected_files = analysis.metadata.files_analyzed

    for path, observation in analysis.parameters.observations.items():
        analysis.parameters.classifications[path] = (
            _classify_observation(
                observation,
                expected_files,
            )
        )


def _classify_observation(
    observation: dict[str, Any],
    expected_files: int,
) -> dict[str, Any]:
    """Return the classification for one parameter."""

    result: dict[str, Any] = {
        "classification": "constant",
    }

    if observation["seen_in_files"] != expected_files:
        result["classification"] = "structural_conflict"
        result["reason"] = "missing_parameter"
        return result

    if len(observation["types"]) != 1:
        result["classification"] = "structural_conflict"
        result["reason"] = "mixed_types"
        return result

    values = list(observation["values"].values())

    if len(values) == 1:
        result["value"] = values[0]["value"]
        return result

    result["classification"] = "varying"

    first_value = values[0]["value"]

    if isinstance(first_value, (int, float)) and not isinstance(first_value, bool):
        numeric_values = [
            item["value"]
            for item in values
        ]

        result["observed_min"] = min(numeric_values)
        result["observed_max"] = max(numeric_values)

    else:
        result["distinct_values"] = [
            item["value"]
            for item in values
        ]

    return result