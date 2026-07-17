"""Load and validate Shape Set Analyzer configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when the program configuration cannot be used."""


def find_config_file() -> Path:
    """Return the config.json path in the current working directory."""
    return Path.cwd() / "config.json"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load config.json and perform basic validation."""
    path = config_path or find_config_file()

    if not path.exists():
        raise ConfigError(
            f"Configuration file not found: {path}\n"
            "Copy config.example.json to config.json and edit the paths."
        )

    try:
        with path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Configuration file contains invalid JSON: {path}\n"
            f"Line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ConfigError(
            f"Unable to read configuration file: {path}\n{exc}"
        ) from exc

    validate_config(config)

    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate the minimum configuration needed by the MVP."""
    paths = config.get("paths")

    if not isinstance(paths, dict):
        raise ConfigError("Configuration must contain a 'paths' object.")

    required_paths = (
        "projects_directory",
        "reports_directory",
        "base_import_directory",
    )

    for name in required_paths:
        value = paths.get(name)

        if not isinstance(value, str) or not value.strip():
            raise ConfigError(
                f"Configuration path '{name}' must be a non-empty string."
            )


def ensure_program_directories(config: dict[str, Any]) -> None:
    """Create writable program-owned directories when they do not exist."""
    paths = config["paths"]

    for name in ("projects_directory", "reports_directory"):
        directory = Path(paths[name])

        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigError(
                f"Unable to create {name}: {directory}\n{exc}"
            ) from exc
        
def save_config(
    config: dict[str, Any],
    config_path: Path | None = None,
) -> None:
    """Write the current program configuration."""
    path = config_path or Path.cwd() / "config.json"
    temporary_path = path.with_suffix(".json.tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)
            file.write("\n")

        temporary_path.replace(path)

    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink(missing_ok=True)

        raise ConfigError(
            f"Unable to write configuration file: {path}\n{exc}"
        ) from exc