"""Configuration support for Shape Set Analyzer."""

from .loader import ConfigError, ensure_program_directories, load_config

__all__ = [
    "ConfigError",
    "ensure_program_directories",
    "load_config",
]