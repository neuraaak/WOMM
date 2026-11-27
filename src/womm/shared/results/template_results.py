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


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "TemplateExtractionReport",
    "TemplateInitResult",
    "TemplateListResult",
    "TemplateStoreResult",
]
