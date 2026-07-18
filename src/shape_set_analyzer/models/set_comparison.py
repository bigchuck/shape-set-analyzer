"""Transient comparison support for stored shape-set analyses."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ComparisonRow:
    """One formatted comparison row."""

    name: str
    difference: str
    first_value: str
    second_value: str
    sort_difference: float = 0.0


def build_parameter_rows(
    first: dict[str, Any],
    second: dict[str, Any],
) -> list[ComparisonRow]:
    """Return every parameter in deterministic path order."""
    first = _flatten_parameter_section(first)
    second = _flatten_parameter_section(second)
    names = sorted(set(first) | set(second), key=str.casefold)
    rows: list[ComparisonRow] = []

    for name in names:
        first_item = first.get(name)
        second_item = second.get(name)
        first_display, first_numeric = _parameter_value(first_item)
        second_display, second_numeric = _parameter_value(second_item)

        rows.append(
            ComparisonRow(
                name=name,
                difference=_difference_text(
                    first_numeric,
                    second_numeric,
                    first_display,
                    second_display,
                ),
                first_value=first_display,
                second_value=second_display,
            )
        )

    return rows


def build_measurement_rows(
    first: dict[str, Any],
    second: dict[str, Any],
) -> list[ComparisonRow]:
    """Return measurements sorted by descending normalized mean difference."""
    rows: list[ComparisonRow] = []

    for stored_name in set(first) & set(second):
        name = _flatten_measurement_name(stored_name)
        first_mean = _measurement_mean(first.get(stored_name))
        second_mean = _measurement_mean(second.get(stored_name))
        first_display = _format_measurement_value(name, first_mean)
        second_display = _format_measurement_value(name, second_mean)
        sort_difference = _normalized_difference(first_mean, second_mean)

        rows.append(
            ComparisonRow(
                name=name,
                difference=_difference_text(
                    first_mean,
                    second_mean,
                    first_display,
                    second_display,
                ),
                first_value=first_display,
                second_value=second_display,
                sort_difference=sort_difference,
            )
        )

    return sorted(
        rows,
        key=lambda row: (-row.sort_difference, row.name.casefold()),
    )


def _flatten_parameter_section(
    section: dict[str, Any],
) -> dict[str, Any]:
    """Return comparison-only parameter names and expanded operations."""
    flattened: dict[str, Any] = {}

    for stored_name, classification in section.items():
        name = _flatten_parameter_name(stored_name)

        if name == "operations":
            operations = _expand_operations(classification)
            if operations:
                flattened.update(operations)
                continue

        flattened[name] = classification

    return flattened


def _flatten_parameter_name(name: str) -> str:
    """Remove internal procedure hierarchy from a parameter name."""
    for prefix in ("procedure.parameters.", "procedure."):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _flatten_measurement_name(name: str) -> str:
    """Remove the internal statistics hierarchy from a report name."""
    prefix = "procedure.statistics."
    if name.startswith(prefix):
        return name[len(prefix):]
    return name


def _expand_operations(classification: Any) -> dict[str, Any]:
    """Expand an operations list into one classification per operation."""
    if not isinstance(classification, dict):
        return {}

    if "value" in classification:
        operation_sets = [classification["value"]]
    elif "distinct_values" in classification:
        operation_sets = classification["distinct_values"]
    else:
        return {}

    mappings: list[dict[str, Any]] = []
    for operation_set in operation_sets:
        mapping = _operation_mapping(operation_set)
        if mapping is None:
            return {}
        mappings.append(mapping)

    operation_names = sorted(
        {name for mapping in mappings for name in mapping},
        key=str.casefold,
    )
    expanded: dict[str, Any] = {}

    for operation_name in operation_names:
        values = [
            mapping[operation_name]
            for mapping in mappings
            if operation_name in mapping
        ]
        path = f"operations.{operation_name}"

        if len(values) != len(mappings):
            expanded[path] = {
                "classification": "structural_conflict",
                "reason": "missing_operation",
            }
        elif all(value == values[0] for value in values[1:]):
            expanded[path] = {
                "classification": "constant",
                "value": values[0],
            }
        elif all(_is_number(value) for value in values):
            expanded[path] = {
                "classification": "varying",
                "observed_min": min(values),
                "observed_max": max(values),
            }
        else:
            expanded[path] = {
                "classification": "varying",
                "distinct_values": values,
            }

    return expanded


def _operation_mapping(value: Any) -> dict[str, Any] | None:
    """Convert a list of [operation, value] pairs into a mapping."""
    if not isinstance(value, list):
        return None

    mapping: dict[str, Any] = {}
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
        ):
            return None
        mapping[item[0]] = item[1]

    return mapping


def format_comparison_rows(
    rows: list[ComparisonRow],
    first_name: str,
    second_name: str,
) -> list[str]:
    """Format rows with dynamically sized, fixed-position columns."""
    if not rows:
        return []

    name_width = max(len(row.name) for row in rows)
    difference_width = max(len(row.difference) for row in rows)
    first_values = [f"{first_name}:{row.first_value}" for row in rows]
    first_width = max(len(value) for value in first_values)

    return [
        (
            f"  {row.name:<{name_width}}  "
            f"{row.difference:>{difference_width}}  "
            f"{first_value:<{first_width}}  "
            f"{second_name}:{row.second_value}"
        )
        for row, first_value in zip(rows, first_values)
    ]


def _parameter_value(
    classification: Any,
) -> tuple[str, float | None]:
    if not isinstance(classification, dict):
        return "not present", None

    if "value" in classification:
        value = classification["value"]
        return _format_parameter_value(value), _numeric_value(value)

    if (
        "observed_min" in classification
        and "observed_max" in classification
    ):
        minimum = classification["observed_min"]
        maximum = classification["observed_max"]
        display = (
            f"{_format_parameter_value(minimum)}.."
            f"{_format_parameter_value(maximum)}"
        )
        if _is_number(minimum) and _is_number(maximum):
            return display, (float(minimum) + float(maximum)) / 2.0
        return display, None

    if "distinct_values" in classification:
        values = classification["distinct_values"]
        return json.dumps(values, separators=(",", ":")), None

    reason = classification.get("reason")
    if reason:
        return str(reason), None

    return str(classification.get("classification", "unknown")), None


def _measurement_mean(classification: Any) -> float | None:
    if not isinstance(classification, dict):
        return None

    value = classification.get("mean")
    if not _is_number(value):
        return None

    return float(value)


def _difference_text(
    first_numeric: float | None,
    second_numeric: float | None,
    first_display: str,
    second_display: str,
) -> str:
    if first_display == "not present":
        return "added"
    if second_display == "not present":
        return "removed"

    if first_numeric is not None and second_numeric is not None:
        if first_numeric == 0.0:
            if second_numeric == 0.0:
                return "0.0%"
            return "n/a"

        percent = (second_numeric - first_numeric) / abs(first_numeric) * 100.0
        if math.isclose(percent, 0.0, abs_tol=0.00005):
            percent = 0.0
        return f"{percent:+.1f}%" if percent else "0.0%"

    return "same" if first_display == second_display else "changed"


def _normalized_difference(
    first_value: float | None,
    second_value: float | None,
) -> float:
    if first_value is None or second_value is None:
        return math.inf
    if first_value == 0.0:
        return 0.0 if second_value == 0.0 else math.inf
    return abs(second_value - first_value) / abs(first_value)


def _format_parameter_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return str(value)


def _format_measurement_value(
    measurement_name: str,
    value: float | None,
) -> str:
    if value is None:
        return "not present"
    if measurement_name in {"bounding_area", "polygon_area"}:
        return f"{value / 1000.0:.1f}K"
    return f"{value:.4f}"


def _numeric_value(value: Any) -> float | None:
    if not _is_number(value):
        return None
    return float(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
