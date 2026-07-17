from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ShapeStyle:
    color: str | None
    width: int | float | None
    transparency: float | None
    z_coord: int | float | None
    fill: str | None


@dataclass(frozen=True)
class ShapeProcedure:
    method: str
    parameters: dict[str, Any]
    statistics: dict[str, Any]


@dataclass(frozen=True)
class ShapeMetadata:
    created: str | None
    modified: str | None
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ImportedShape:
    source_file: Path
    name: str
    shape_type: str
    points: tuple[tuple[float, float], ...]

    style: ShapeStyle
    procedure: ShapeProcedure
    metadata: ShapeMetadata