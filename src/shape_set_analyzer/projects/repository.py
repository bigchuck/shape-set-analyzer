"""Storage operations for Shape Set Analyzer projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProjectError(Exception):
    """Raised when a project operation cannot be completed."""


def project_file_path(
    projects_directory: Path,
    project_name: str,
) -> Path:
    """Return the master JSON path for a project."""
    return projects_directory / f"{project_name}.json"


def list_project_names(projects_directory: Path) -> list[str]:
    """Return all known project names in alphabetical order."""
    if not projects_directory.exists():
        return []

    names = [
        path.stem
        for path in projects_directory.glob("*.json")
        if path.is_file()
    ]

    return sorted(names, key=str.casefold)


def project_exists(
    projects_directory: Path,
    project_name: str,
) -> bool:
    """Return True when the named project exists."""
    return project_file_path(projects_directory, project_name).is_file()


def load_project(
    projects_directory: Path,
    project_name: str,
) -> dict[str, Any]:
    """Load a project master JSON file."""
    path = project_file_path(projects_directory, project_name)

    if not path.exists():
        raise ProjectError(f"Project does not exist: {project_name}")

    try:
        with path.open("r", encoding="utf-8") as file:
            project = json.load(file)
    except json.JSONDecodeError as exc:
        raise ProjectError(
            f"Project file contains invalid JSON: {path}\n"
            f"Line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ProjectError(
            f"Unable to read project file: {path}\n{exc}"
        ) from exc

    return project


def save_project(
    projects_directory: Path,
    project_name: str,
    project: dict[str, Any],
) -> None:
    """Write a project master JSON file."""
    projects_directory.mkdir(parents=True, exist_ok=True)

    path = project_file_path(projects_directory, project_name)
    temporary_path = path.with_suffix(".json.tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(project, file, indent=2)
            file.write("\n")

        temporary_path.replace(path)

    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink(missing_ok=True)

        raise ProjectError(
            f"Unable to write project file: {path}\n{exc}"
        ) from exc