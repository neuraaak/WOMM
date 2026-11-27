#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE STORE DISPLAY - Template Catalog Rendering
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Rendering for the template catalog.

This module renders the outcome of ``TemplateStoreInterface`` operations for
the CLI, following the established rendering pattern used by ``path``,
``context``, ``deps`` and ``doctor``: a table for a list of entries, a panel
for a single entry, and an error message on failure.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Third-party imports
from rich.panel import Panel

# Local imports
from ....shared.models.template_source import TemplateEntry
from ....shared.results.template_results import (
    TemplateExtractionReport,
    TemplateListResult,
    TemplateStoreResult,
)
from ...common.logging import ezconsole, ezprinter

# ///////////////////////////////////////////////////////////////
# HELPERS
# ///////////////////////////////////////////////////////////////


def _entry_panel(entry: TemplateEntry, *, verbose: bool) -> Panel:
    """Build a Rich panel describing a single template entry.

    Args:
        entry: Template entry to describe.
        verbose: Whether to also show the source path.

    Returns:
        Panel: A bordered panel ready to print.
    """
    lines = [
        f"[b]Identifier:[/b] {entry.qualified_id}",
        f"[b]Origin:[/b] {entry.origin.value}",
        f"[b]Version:[/b] {entry.version or 'unknown'}",
        f"[b]Description:[/b] {entry.description or 'No description'}",
    ]
    if verbose:
        lines.append(f"[b]Source:[/b] {entry.source}")
        if entry.copied_from is not None:
            lines.append(f"[b]Copied from:[/b] {entry.copied_from}")

    return Panel(
        "\n".join(lines),
        title=f"Template: {entry.qualified_id}",
        border_style="blue",
        padding=(1, 1),
    )


# ///////////////////////////////////////////////////////////////
# DISPLAY FUNCTIONS
# ///////////////////////////////////////////////////////////////


def render_template_list(result: TemplateListResult, *, verbose: bool = False) -> None:
    """Render the outcome of ``TemplateStoreInterface.list_templates``.

    Args:
        result: Outcome returned by ``TemplateStoreInterface.list_templates``.
        verbose: Whether to also show the source path of every entry.
    """
    if not result.success:
        ezprinter.error(result.error or "Failed to list templates")
        return

    entries = result.entries or []
    ezprinter.success(result.message or f"{len(entries)} template(s) available")

    if not entries:
        ezprinter.console.print("")
        ezprinter.system("No template registered")
        return

    columns: list[str] | list[tuple[str, str | None, bool]] = [
        ("Identifier", "cyan", False),
        ("Version", "yellow", True),
        ("Description", "white", False),
    ]
    if verbose:
        columns.append(("Source", "green", False))

    table = ezprinter.create_table(title="Template Catalog", columns=columns)
    for entry in entries:
        row = [entry.qualified_id, entry.version or "-", entry.description or "-"]
        if verbose:
            row.append(str(entry.source))
        table.add_row(*row)

    ezprinter.console.print("")
    ezprinter.console.print(table)


def render_template_result(
    result: TemplateStoreResult, *, verbose: bool = False
) -> None:
    """Render the outcome of a single-template operation.

    Args:
        result: Outcome returned by ``show_template``, ``add_template``,
            ``remove_template`` or ``update_template``.
        verbose: Whether to also show the source path in the panel.
    """
    if not result.success:
        ezprinter.error(result.error or "Template operation failed")
        return

    ezprinter.success(result.message or "Template operation succeeded")
    if result.entry is not None:
        ezconsole.print("")
        ezconsole.print(_entry_panel(result.entry, verbose=verbose))


def render_extraction_report(
    report: TemplateExtractionReport, *, verbose: bool = False
) -> None:
    """Render what ``template init --from`` took from the project.

    Args:
        report: Report carried by the ``template init`` result.
        verbose: Whether to also list every file and residual occurrence.
    """
    lines = [
        f"[b]Copied as is:[/b] {len(report.copied)} file(s)",
        f"[b]With names replaced:[/b] {len(report.transformed)} file(s)",
        f"[b]Excluded:[/b] {len(report.excluded)} file(s)",
    ]
    for variable, name in report.variables.items():
        count = report.replacements.get(variable, 0)
        lines.append(f"[b]{name}[/b] -> {variable} ({count} occurrence(s))")
    if not report.variables:
        lines.append("No project name replaced")
    ezconsole.print("")
    ezconsole.print(
        Panel(
            "\n".join(lines),
            title="Extracted from the project",
            border_style="blue",
            padding=(1, 1),
        )
    )

    reasons: dict[str, int] = {}
    for _path, reason in report.excluded:
        reasons[reason] = reasons.get(reason, 0) + 1
    for reason, count in sorted(reasons.items()):
        ezprinter.info(f"Excluded ({reason}): {count}")
    if verbose:
        for path in report.transformed:
            ezprinter.info(f"Names replaced: {path}")
        for path, reason in report.excluded:
            ezprinter.info(f"Excluded: {path} ({reason})")
    if report.residuals:
        count = len(report.residuals)
        shown = f"At least {count}" if report.residuals_truncated else str(count)
        ezprinter.warning(
            f"{shown} line(s) still mention the project name"
            " in another form: review them"
        )
        if verbose:
            for location in report.residuals:
                ezprinter.info(f"Residual: {location}")
    for warning in report.warnings:
        ezprinter.warning(warning)
    ezprinter.warning(
        "Name replacement is heuristic: review the template before sharing it"
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "render_extraction_report",
    "render_template_list",
    "render_template_result",
]
