"""Discover ShapeStudio JSON files for import."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ImportScanError(Exception):
    """Raised when an import directory cannot be scanned."""


@dataclass(frozen=True)
class ScanSummary:
    """Results from scanning a ShapeStudio directory."""

    directory: Path
    prefix: str
    files: list[Path]

    @property
    def file_count(self) -> int:
        """Return the number of discovered files."""
        return len(self.files)


def find_shape_files(
    directory: Path,
    prefix: str,
) -> list[Path]:
    """Find JSON files having the requested filename prefix."""
    if not directory.exists():
        raise ImportScanError(
            f"Import directory does not exist: {directory}"
        )

    if not directory.is_dir():
        raise ImportScanError(
            f"Import path is not a directory: {directory}"
        )

    prefix = prefix.strip()

    if not prefix:
        raise ImportScanError("Filename prefix cannot be empty.")

    pattern = f"{prefix}_*.json"

    try:
        files = [
            path
            for path in directory.glob(pattern)
            if path.is_file()
        ]
    except OSError as exc:
        raise ImportScanError(
            f"Unable to scan import directory: {directory}\n{exc}"
        ) from exc

    return sorted(
        files,
        key=lambda path: path.name.casefold(),
    )

def summarize_directory(
    directory: Path,
    prefix: str,
) -> ScanSummary:
    """Scan a directory for JSON files with the supplied prefix."""
    files = find_shape_files(
        directory=directory,
        prefix=prefix,
    )

    return ScanSummary(
        directory=directory,
        prefix=prefix,
        files=files,
    )