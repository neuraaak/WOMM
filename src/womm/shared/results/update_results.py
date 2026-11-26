"""Presentation-independent report for a project tooling update."""

from dataclasses import dataclass, field
from pathlib import Path

from .base import BaseResult


@dataclass
class ToolingUpdateResult(BaseResult):
    """Resolved versions and migration summaries, without configuration values."""

    updates: list[tuple[str, str, str]] = field(default_factory=list)
    migrations: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    dry_run: bool = False
