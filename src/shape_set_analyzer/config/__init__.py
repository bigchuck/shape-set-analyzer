"""Configuration support."""

from .loader import (
    ConfigError,
    ensure_program_directories,
    load_config,
    save_config,
)

__all__ = [
    "ConfigError",
    "ensure_program_directories",
    "load_config",
    "save_config",
]