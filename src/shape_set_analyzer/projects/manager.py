"""Higher-level project management operations."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .repository import (
    ProjectError,
    list_project_names,
    load_project,
    project_exists,
    save_project,
)


PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def current_timestamp() -> str:
    """Return a local ISO-format timestamp."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def validate_project_name(project_name: str) -> str:
    """Validate and normalize a project name."""
    name = project_name.strip()

    if not name:
        raise ProjectError("Project name cannot be empty.")

    if not PROJECT_NAME_PATTERN.fullmatch(name):
        raise ProjectError(
            "Project names may contain only letters, numbers, "
            "hyphens, and underscores."
        )

    return name


def create_project(
    projects_directory: Path,
    project_name: str,
) -> dict[str, Any]:
    """Create and save a new empty project."""
    name = validate_project_name(project_name)

    if project_exists(projects_directory, name):
        raise ProjectError(f"Project already exists: {name}")

    timestamp = current_timestamp()

    project = {
        "schema_version": "1.0",
        "analysis_version": "1.0",
        "project": {
            "name": name,
            "created": timestamp,
            "modified": timestamp,
        },
        "sets": {},
    }
    save_project(projects_directory, name, project)
    return project

from datetime import datetime
from typing import Any


def add_set_to_project(
    projects_directory,
    project: dict[str, Any],
    set_name: str,
    set_data: dict[str, Any],
) -> None:
    """Add an imported shape set and save the project."""

    sets = project.setdefault("sets", {})

    if set_name in sets:
        raise ProjectError(
            f"Set already exists in project: {set_name}"
        )

    sets[set_name] = set_data

    project["project"]["modified"] = (
        datetime.now().isoformat()
    )

    project_name = project["project"]["name"]

    save_project(
        projects_directory,
        project_name,
        project,
    )


def get_project(
    projects_directory: Path,
    project_name: str,
) -> dict[str, Any]:
    """Load a named project."""
    name = validate_project_name(project_name)
    return load_project(projects_directory, name)


def get_project_names(projects_directory: Path) -> list[str]:
    """Return known project names."""
    return list_project_names(projects_directory)