from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shape_set_analyzer.models.imported_shape import (
    ImportedShape,
    ShapeMetadata,
    ShapeProcedure,
    ShapeStyle,
)


class ShapeImportError(Exception):
    """Raised when a ShapeStudio file cannot be imported."""


def read_shape_file(path: Path) -> ImportedShape:
    """Read one ShapeStudio JSON file into an ImportedShape."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise ShapeImportError(
            f"Shape file does not exist: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ShapeImportError(
            f"Invalid JSON in shape file: {path}"
        ) from exc
    except OSError as exc:
        raise ShapeImportError(
            f"Unable to read shape file: {path}"
        ) from exc

    try:
        attrs = _require_mapping(data, "attrs")
        geometry = _require_mapping(attrs, "geometry")
        procedure_data = _require_mapping(attrs, "procedure")

        top_level_type = _require_string(data, "type")
        attrs_type = _require_string(attrs, "type")

        if top_level_type != attrs_type:
            raise ShapeImportError(
                f"Shape type mismatch in {path}: "
                f"{top_level_type!r} != {attrs_type!r}"
            )

        points = _read_points(
            geometry.get("points"),
            path=path,
        )

        style_data = _optional_mapping(attrs.get("style"))
        metadata_data = _optional_mapping(attrs.get("metadata"))

        return ImportedShape(
            source_file=path,
            name=_require_string(data, "name"),
            shape_type=top_level_type,
            points=points,
            style=_read_style(style_data),
            procedure=_read_procedure(procedure_data),
            metadata=_read_metadata(metadata_data),
        )

    except ShapeImportError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ShapeImportError(
            f"Invalid ShapeStudio structure in {path}: {exc}"
        ) from exc


def _read_points(
    value: Any,
    *,
    path: Path,
) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, list):
        raise ShapeImportError(
            f"Geometry points must be a list in {path}"
        )

    points: list[tuple[float, float]] = []

    for index, point in enumerate(value):
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(
                isinstance(coordinate, (int, float))
                for coordinate in point
            )
        ):
            raise ShapeImportError(
                f"Invalid point at index {index} in {path}"
            )

        points.append((point[0], point[1]))

    if len(points) < 3:
        raise ShapeImportError(
            f"Polygon must contain at least three points: {path}"
        )

    return tuple(points)


def _read_style(data: dict[str, Any]) -> ShapeStyle:
    return ShapeStyle(
        color=data.get("color"),
        width=data.get("width"),
        transparency=data.get("transparency"),
        z_coord=data.get("z_coord"),
        fill=data.get("fill"),
    )


def _read_procedure(
    data: dict[str, Any],
) -> ShapeProcedure:
    method = data.get("method")

    if not isinstance(method, str) or not method:
        raise ShapeImportError(
            "Procedure method is missing or invalid."
        )

    parameters = _optional_mapping(
        data.get("parameters")
    )
    statistics = _optional_mapping(
        data.get("statistics")
    )

    return ShapeProcedure(
        method=method,
        parameters=parameters,
        statistics=statistics,
    )


def _read_metadata(
    data: dict[str, Any],
) -> ShapeMetadata:
    tags = data.get("tags", [])

    if not isinstance(tags, list):
        raise ShapeImportError(
            "Metadata tags must be a list."
        )

    return ShapeMetadata(
        created=data.get("created"),
        modified=data.get("modified"),
        tags=tuple(str(tag) for tag in tags),
    )


def _require_mapping(
    data: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = data.get(key)

    if not isinstance(value, dict):
        raise ShapeImportError(
            f"Required object is missing or invalid: {key}"
        )

    return value


def _optional_mapping(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ShapeImportError(
            "Expected a JSON object."
        )

    return value


def _require_string(
    data: dict[str, Any],
    key: str,
) -> str:
    value = data.get(key)

    if not isinstance(value, str) or not value:
        raise ShapeImportError(
            f"Required string is missing or invalid: {key}"
        )

    return value

def import_shape_set(
    files: list[Path],
    *,
    source: str,
) -> dict[str, Any]:
    """Read ShapeStudio files and build one project set manifest."""
    file_references: list[dict[str, Any]] = []
    source_directory = Path(source).parent

    for path in files:
        shape = read_shape_file(path)
        relative_path = source_directory / path.name

        file_references.append(
            {
                "relative_path": relative_path.as_posix(),
                "shape_name": shape.name,
                "modified": shape.metadata.modified,
            }
        )

    return {
        "source": source,
        "file_count": len(file_references),
        "files": file_references,
    }
