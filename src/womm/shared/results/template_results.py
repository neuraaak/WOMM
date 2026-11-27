#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE RESULTS - Template catalog result types
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Typed results returned by the template store."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any

from womm.shared.models.template_source import TemplateEntry

from .base import BaseResult
from .project_results import ProjectCreationResult

# ///////////////////////////////////////////////////////////////
# RESULTS
# ///////////////////////////////////////////////////////////////


@dataclass
class TemplateStoreResult(BaseResult):
    """Result of an operation targeting a single template."""

    entry: TemplateEntry | None = None


@dataclass
class TemplateListResult(BaseResult):
    """Result of listing the template catalog."""

    entries: list[TemplateEntry] | None = None


@dataclass
class TemplateExtractionReport:
    """What ``template init --from`` took from a project, and how.

    Paths are relative to the source project: the report never carries an
    absolute path of the machine.

    Attributes:
        copied: Files copied byte for byte.
        transformed: Files whose project names became template variables.
        excluded: ``(path, reason)`` for every tracked file left out.
        replacements: Number of replaced occurrences, per variable.
        variables: Source string replaced by each variable.
        residuals: ``path:line`` of name variants left untouched.
        residuals_truncated: Whether ``residuals`` stopped at its limit.
        warnings: Points the template author must review.
    """

    copied: list[str] = field(default_factory=list)
    transformed: list[str] = field(default_factory=list)
    excluded: list[tuple[str, str]] = field(default_factory=list)
    replacements: dict[str, int] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    residuals: list[str] = field(default_factory=list)
    residuals_truncated: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class TemplateInitResult(ProjectCreationResult):
    """Result of ``template init``, with the extraction report when ``--from``."""

    extraction: TemplateExtractionReport | None = None


class ChangeKind(StrEnum):
    """What a project file asks of the template."""

    UPDATED = "updated"  # changed in the project only: applied
    NEW = "new"  # new in the project: integrate it?
    REMOVABLE = "removable"  # gone from the project: delete it?
    CONFLICT = "conflict"  # both sides changed: keep mine or take the new one?


@dataclass(frozen=True)
class FileChange:
    """One action the update proposes for one project file.

    Attributes:
        source: Path of the file in the project.
        kind: What the change asks.
        current: Where the file is in the template now, if anywhere.
        target: Where the new content goes; None when taking it means deleting.
        content: New content, None when the project no longer has the file.
        reason: Why a conflict is one.
        mode: Permission bits of the project file, for a file created anew.
    """

    source: PurePosixPath
    kind: ChangeKind
    current: PurePosixPath | None
    target: PurePosixPath | None
    content: bytes | None
    reason: str = ""
    mode: int = 0


@dataclass(frozen=True)
class UpdateOutcome:
    """What an applied update changed in the template."""

    written: list[str]
    removed: list[str]
    pending: list[str]
    version: tuple[str, str] | None  # (before, after) when bumped


@dataclass
class TemplateUpdatePreview(BaseResult):
    """What ``template update`` would do, shown before anything is written.

    Attributes:
        template: Template directory the update targets.
        entry: Catalog entry whose copy will be refreshed, if any.
        other_ids: Entries copied from ``template`` when more than one is.
        changes: Changes from the project, automatic ones and questions.
        unchanged: Project files the template already matches.
        kept: Project files the template author changed or deleted.
        report: Extraction report of the project, when one was made.
        plan: Opaque plan handed back to ``apply_update``.
    """

    template: Path | None = None
    entry: TemplateEntry | None = None
    other_ids: list[str] = field(default_factory=list)
    changes: list[FileChange] = field(default_factory=list)
    unchanged: int = 0
    kept: int = 0
    report: TemplateExtractionReport | None = None
    plan: Any = None

    def questions(self) -> list[FileChange]:
        """Changes the author decides on."""
        return [c for c in self.changes if c.kind is not ChangeKind.UPDATED]


@dataclass
class TemplateUpdateResult(BaseResult):
    """Outcome of ``template update``.

    Attributes:
        outcome: What changed in the template, when it was updated.
        entry: The refreshed catalog entry, when the store was updated.
        store_error: Why the store was not updated although it should have.
    """

    outcome: UpdateOutcome | None = None
    entry: TemplateEntry | None = None
    store_error: str = ""


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "ChangeKind",
    "FileChange",
    "TemplateExtractionReport",
    "TemplateInitResult",
    "TemplateListResult",
    "TemplateStoreResult",
    "TemplateUpdatePreview",
    "TemplateUpdateResult",
    "UpdateOutcome",
]
