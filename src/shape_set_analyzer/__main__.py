"""Command-line entry point for Shape Set Analyzer."""

from __future__ import annotations

import shlex
from pathlib import Path

from . import __version__
from .config import (
    ConfigError,
    ensure_program_directories,
    load_config,
    save_config,
)
from .projects import (
    ProjectError,
    add_set_to_project,
    create_project,
    get_project,
    get_project_names,
)

from .imports import (
    ImportScanError,
    import_shape_set,
    summarize_directory,
)
from shape_set_analyzer.imports.importer import read_shape_file

def show_help() -> None:
    """Display available commands."""
def show_help() -> None:
    """Display available commands."""
    print()
    print("Available commands:")
    print()
    print("  help                         Show this help")
    print("  status                       Show program status")
    print("  list projects                List all projects")
    print("  create project <name>        Create a project")
    print("  set project <name>           Set active project")
    print("  show project                 Show active project")
    print("  add set <name> from <dir>    Scan files for a new set")
    print("  verify set <name>            Verify stored source files")
    print("  report set <name>            Report stored set analysis")
    print("  quit                         Exit")
    print()

def get_projects_directory(config: dict) -> Path:
    """Return the configured projects directory."""
    return Path(config["paths"]["projects_directory"])


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
        "  Base import exists:    "
        f"{'yes' if base_import.is_dir() else 'no'}"
    )
    print()


def show_project_list(config: dict) -> None:
    """Display all known projects."""
    projects_directory = get_projects_directory(config)
    project_names = get_project_names(projects_directory)
    active_project = config.get("active_project")

    print()
    print("KNOWN PROJECTS")
    print()

    if not project_names:
        print("  No projects have been created.")
    else:
        for name in project_names:
            marker = "*" if name == active_project else " "
            print(f"  {marker} {name}")

    print()
    print(f"Active project: {active_project or 'none'}")
    print()


def handle_create_project(config: dict, project_name: str) -> None:
    """Create a new project."""
    projects_directory = get_projects_directory(config)
    project = create_project(projects_directory, project_name)
    name = project["project"]["name"]

    print()
    print(f"Project created: {name}")
    print(f"Master file: {projects_directory / f'{name}.json'}")
    print()


def handle_set_project(config: dict, project_name: str) -> None:
    """Set and persist the active project."""
    projects_directory = get_projects_directory(config)
    project = get_project(projects_directory, project_name)
    name = project["project"]["name"]

    config["active_project"] = name
    save_config(config)

    print()
    print(f"Active project set to: {name}")
    print(f"Sets stored: {len(project.get('sets', {}))}")
    print()


def handle_show_project(config: dict) -> None:
    """Display the active project summary."""
    active_project = config.get("active_project")

    if not active_project:
        raise ProjectError(
            "No active project. Use 'set project <name>'."
        )

    projects_directory = get_projects_directory(config)
    project = get_project(projects_directory, active_project)

    metadata = project["project"]
    sets = project.get("sets", {})

    print()
    print(f"PROJECT: {metadata['name']}")
    print()
    print(f"  Created:          {metadata['created']}")
    print(f"  Modified:         {metadata['modified']}")
    print(f"  Schema version:   {project['schema_version']}")
    print(f"  Analysis version: {project['analysis_version']}")
    print(f"  Sets stored:      {len(sets)}")
    print(f"  Master file:      {projects_directory / f'{active_project}.json'}")
    print()


def handle_verify_set(config: dict, set_name: str) -> None:
    """Verify that a stored set's source files still exist and are unchanged."""
    active_project = config.get("active_project")

    if not active_project:
        raise ProjectError(
            "No active project. Use 'set project <name>'."
        )

    projects_directory = get_projects_directory(config)
    project = get_project(projects_directory, active_project)
    sets = project.get("sets", {})

    if set_name not in sets:
        raise ProjectError(
            f"Set does not exist in project: {set_name}"
        )

    set_data = sets[set_name]
    file_references = set_data.get("files", [])
    base_import_directory = Path(
        config["paths"]["base_import_directory"]
    )

    missing_files: list[str] = []
    modified_files: list[str] = []
    additional_files: list[str] = []

    for file_reference in file_references:
        relative_path = file_reference["relative_path"]
        source_path = Path(relative_path)

        if not source_path.is_absolute():
            source_path = base_import_directory / source_path

        if not source_path.is_file():
            missing_files.append(relative_path)
            continue

        shape = read_shape_file(source_path)

        if shape.metadata.modified != file_reference.get("modified"):
            modified_files.append(relative_path)

    source_spec = set_data.get("source", "").strip().rstrip("/\\")

    if source_spec:
        source_spec_path = Path(source_spec)
        source_prefix = source_spec_path.name

        if source_spec_path.is_absolute():
            source_directory = source_spec_path.parent
        else:
            source_directory = (
                base_import_directory / source_spec_path.parent
            )

        current_summary = summarize_directory(
            directory=source_directory.resolve(),
            prefix=source_prefix,
        )
        manifest_paths = {
            Path(file_reference["relative_path"]).as_posix()
            for file_reference in file_references
        }

        for current_path in current_summary.files:
            if source_spec_path.is_absolute():
                current_reference = current_path.as_posix()
            else:
                current_reference = (
                    source_spec_path.parent / current_path.name
                ).as_posix()

            if current_reference not in manifest_paths:
                additional_files.append(current_reference)

    print()
    print(f'VERIFY SET: "{set_name}"')
    print()
    print(f"  Manifest files: {len(file_references)}")
    print(f"  Missing:        {len(missing_files)}")
    print(f"  Modified:       {len(modified_files)}")
    print(f"  Additional:     {len(additional_files)}")

    if missing_files:
        print()
        print("  Missing files:")
        for relative_path in missing_files[:5]:
            print(f"    {relative_path}")
        if len(missing_files) > 5:
            print(
                f"    ... {len(missing_files) - 5} more missing files"
            )

    if modified_files:
        print()
        print("  Modified files:")
        for relative_path in modified_files[:5]:
            print(f"    {relative_path}")
        if len(modified_files) > 5:
            print(
                f"    ... {len(modified_files) - 5} more modified files"
            )

    if additional_files:
        print()
        print("  Additional matching files:")
        for relative_path in additional_files[:5]:
            print(f"    {relative_path}")
        if len(additional_files) > 5:
            print(
                f"    ... {len(additional_files) - 5} more additional files"
            )
        print()
        print("  The set may need to be rebuilt.")

    print()
    if missing_files or modified_files or additional_files:
        print("  Status: verification failed.")
    else:
        print("  Status: verified.")
    print()

def format_report_value(
    measurement_name: str,
    field_name: str,
    value: object,
) -> str:
    """Format one value for the simple set report."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)

    if (
        measurement_name in {"bounding_area", "polygon_area"}
        and field_name != "count"
    ):
        return f"{value / 1000.0:.1f}K"

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value)

def handle_report_set(config: dict, set_name: str) -> None:
    """Display the stored analysis for one set."""
    active_project = config.get("active_project")

    if not active_project:
        raise ProjectError(
            "No active project. Use 'set project <name>'."
        )

    projects_directory = get_projects_directory(config)
    project = get_project(projects_directory, active_project)
    sets = project.get("sets", {})

    if set_name not in sets:
        raise ProjectError(
            f"Set does not exist in project: {set_name}"
        )

    set_data = sets[set_name]
    analysis = set_data.get("analysis")

    if not isinstance(analysis, dict):
        raise ProjectError(
            f"Set has no stored analysis; rebuild set: {set_name}"
        )

    print()
    print(f'SET REPORT: "{set_name}"')
    print()
    print(f"  Files analyzed: {set_data.get('file_count', 0)}")

    for title, section_name in (
        ("PARAMETERS", "parameters"),
        ("STATISTICS", "statistics"),
        ("GEOMETRY", "geometry"),
    ):
        section = analysis.get(section_name, {})

        print()
        print(title)
        print()

        if not section:
            print("  No values recorded.")
            continue

        for name in sorted(section, key=str.casefold):
            print(f"  {name}")

            for field, value in section[name].items():
                formatted_value = format_report_value(
                    name,
                    field,
                    value,
                )
                print(f"    {field}: {formatted_value}")

    print()

def get_prompt(config: dict) -> str:
    """Return the interactive prompt."""
    active_project = config.get("active_project")

    if active_project:
        return f"shape-analyzer[{active_project}]> "

    return "shape-analyzer> "


def process_command(command: str, config: dict) -> bool:
    """
    Process one command.

    Return False when the program should exit.
    """
    try:
        parts = shlex.split(command, posix=False)
    except ValueError as exc:
        print(f"Unable to parse command: {exc}")
        return True

    if not parts:
        return True

    normalized = [part.lower() for part in parts]

    if normalized[0] in {"quit", "exit"}:
        return False

    if normalized == ["help"]:
        show_help()
        return True

    if normalized == ["status"]:
        show_status(config)
        return True

    if normalized == ["list", "projects"]:
        show_project_list(config)
        return True

    if len(parts) == 3 and normalized[:2] == ["create", "project"]:
        handle_create_project(config, parts[2])
        return True

    if len(parts) == 3 and normalized[:2] == ["set", "project"]:
        handle_set_project(config, parts[2])
        return True

    if normalized == ["show", "project"]:
        handle_show_project(config)
        return True

    if len(parts) == 3 and normalized[:2] == ["verify", "set"]:
        handle_verify_set(config, parts[2])
        return True
    
    if len(parts) == 3 and normalized[:2] == ["report", "set"]:
        handle_report_set(config, parts[2])
        return True
    
    if (
        len(parts) == 5
        and normalized[:2] == ["add", "set"]
        and normalized[3] == "from"
    ):
        handle_add_set_scan(
            config,
            set_name=parts[2],
            source_spec=parts[4],
        )
        return True
    
    print(f"Unknown command: {command}")
    print("Type 'help' to see available commands.")
    return True


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
            command = input(get_prompt(config)).strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        try:
            keep_running = process_command(command, config)
        except (ProjectError, ConfigError, ImportScanError) as exc:
            print()
            print(f"Error: {exc}")
            print()
            continue

        if not keep_running:
            break

def handle_add_set_scan(
    config: dict,
    set_name: str,
    source_spec: str,
) -> None:
    """
    Scan ShapeStudio files and save the first matching file as a set.

    Example:

        add set x from sa224/gen4

    Meaning:

        directory = <base_import_directory>/sa224
        prefix    = gen4
        pattern   = gen4_*.json
    """

    active_project = config.get("active_project")

    if not active_project:
        raise ProjectError(
            "No active project. Use 'set project <name>'."
        )

    set_name = set_name.strip()

    if not set_name:
        raise ImportScanError(
            "Set name cannot be empty."
        )

    source_spec = source_spec.strip().rstrip("/\\")

    if not source_spec:
        raise ImportScanError(
            "Source specification cannot be empty."
        )

    source_path = Path(source_spec)

    prefix = source_path.name
    relative_directory = source_path.parent

    if not prefix:
        raise ImportScanError(
            "Filename prefix cannot be empty."
        )

    base_import_directory = Path(
        config["paths"]["base_import_directory"]
    )

    if source_path.is_absolute():
        import_directory = source_path.parent
    else:
        import_directory = (
            base_import_directory / relative_directory
        )

    import_directory = import_directory.resolve()

    summary = summarize_directory(
        directory=import_directory,
        prefix=prefix,
    )

    first_shape = None

    if summary.files:
        first_shape = read_shape_file(
            summary.files[0]
        )

        projects_directory = get_projects_directory(config)

        project = get_project(
            projects_directory,
            active_project,
        )

        set_data = import_shape_set(
            summary.files,
            source=source_spec,
        )

        add_set_to_project(
            projects_directory,
            project,
            set_name,
            set_data,
        )

    print()
    print(f"Scanning directory : {summary.directory}")
    print(f"Filename pattern   : {summary.prefix}_*.json")
    print(f"JSON files found   : {summary.file_count}")
    print(f'Proposed set name  : "{set_name}"')

    if summary.file_count == 0:
        print("No matching ShapeStudio files were found.")
    else:
        print(
            "One-file set saved to the active project."
        )

    if first_shape is not None:
        print()
        print(
            f"First file read    : "
            f"{first_shape.source_file.name}"
        )
        print(
            f"Shape type         : "
            f"{first_shape.shape_type}"
        )
        print(
            f"Vertices           : "
            f"{len(first_shape.points)}"
        )
        print(
            f"Procedure          : "
            f"{first_shape.procedure.method}"
        )

    print()

if __name__ == "__main__":
    main()
