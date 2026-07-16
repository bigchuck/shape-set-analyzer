"""Command-line entry point for Shape Set Analyzer."""

from pathlib import Path

from . import __version__
from .config import ConfigError, ensure_program_directories, load_config


def show_help() -> None:
    """Display available commands."""
    print()
    print("Available commands:")
    print("  help      Show this help")
    print("  status    Show program status")
    print("  quit      Exit the program")
    print()


def show_status(config: dict) -> None:
    """Display configuration and path status."""
    paths = config["paths"]
    base_import = Path(paths["base_import_directory"])

    print()
    print("PROGRAM STATUS")
    print()
    print(f"  Version:               {__version__}")
    print(f"  Active project:        {config.get('active_project') or 'none'}")
    print(f"  Projects directory:    {paths['projects_directory']}")
    print(f"  Reports directory:     {paths['reports_directory']}")
    print(f"  Base import directory: {base_import}")
    print(
        f"  Base import exists:    "
        f"{'yes' if base_import.is_dir() else 'no'}"
    )
    print()


def main() -> None:
    """Run the interactive CLI."""
    try:
        config = load_config()
        ensure_program_directories(config)
    except ConfigError as exc:
        print("Shape Set Analyzer could not start.")
        print()
        print(exc)
        raise SystemExit(1) from exc

    print(f"Shape Set Analyzer {__version__}")
    print("Type 'help' for assistance or 'quit' to exit.")
    print()

    while True:
        try:
            command = input("shape-analyzer> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        if not command:
            continue

        command_lower = command.lower()

        if command_lower in {"quit", "exit"}:
            break

        if command_lower == "help":
            show_help()
            continue

        if command_lower == "status":
            show_status(config)
            continue

        print(f"Unknown command: {command}")
        print("Type 'help' to see available commands.")


if __name__ == "__main__":
    main()