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
    ChangeKind,
    TemplateExtractionReport,
    TemplateListResult,
    TemplateStoreResult,
    TemplateUpdatePreview,
    TemplateUpdateResult,
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
        if entry.store_version:
            lines.append(
                f"[b]Stored version:[/b] v{entry.store_version}"
                f" ({entry.store_versions} kept)"
            )
            for item in entry.store_history:
                mark = "*" if item.number == entry.store_version else " "
                details = " ".join(
                    part for part in (item.template_version, item.created) if part
                )
                lines.append(f"  {mark} v{item.number}  {details}".rstrip())

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


CHANGE_LABELS = {
    ChangeKind.UPDATED: "Updated from the project",
    ChangeKind.NEW: "New in the project",
    ChangeKind.REMOVABLE: "Gone from the project",
    ChangeKind.CONFLICT: "Conflicts",
}


def render_update_preview(
    preview: TemplateUpdatePreview, *, verbose: bool = False
) -> None:
    """Render what ``template update`` is about to do.

    Args:
        preview: Successful result of ``plan_update``.
        verbose: Whether to list every file of each category.
    """
    lines = [f"[b]Template:[/b] {preview.template or '-'}"]
    if preview.entry is not None:
        lines.append(f"[b]Store entry:[/b] {preview.entry.qualified_id}")
    if preview.report is not None:
        lines.append(f"[b]Already up to date:[/b] {preview.unchanged} file(s)")
        lines.append(f"[b]Your edits kept:[/b] {preview.kept} file(s)")
        for kind, label in CHANGE_LABELS.items():
            count = sum(1 for c in preview.changes if c.kind is kind)
            lines.append(f"[b]{label}:[/b] {count} file(s)")
    else:
        lines.append("No extraction trace: only the store copy is refreshed")
    ezconsole.print("")
    ezconsole.print(
        Panel(
            "\n".join(lines),
            title="Template update",
            border_style="blue",
            padding=(1, 1),
        )
    )
    if verbose:
        for change in preview.changes:
            ezprinter.info(f"{CHANGE_LABELS[change.kind]}: {change.source}")
    if preview.other_ids:
        ezprinter.warning(
            "Several store entries come from this template: "
            + ", ".join(preview.other_ids)
            + ". Refresh them with womm template update ID."
        )


def render_update_result(
    result: TemplateUpdateResult, *, verbose: bool = False
) -> None:
    """Render the outcome of ``apply_update``.

    Args:
        result: Outcome returned by ``apply_update``.
        verbose: Whether to list every written and removed file.
    """
    if not result.success:
        ezprinter.error(result.error or "Template update failed")
        return
    outcome = result.outcome
    if outcome is not None:
        if outcome.version is not None:
            before, after = outcome.version
            ezprinter.success(f"Template updated: version {before} -> {after}")
        else:
            ezprinter.success("Template already up to date: nothing was changed")
        ezprinter.info(
            f"Written: {len(outcome.written)}, removed: {len(outcome.removed)}"
        )
        if verbose:
            for path in outcome.written:
                ezprinter.info(f"Written: {path}")
            for path in outcome.removed:
                ezprinter.info(f"Removed: {path}")
        if outcome.pending:
            ezprinter.warning(
                f"{len(outcome.pending)} question(s) left for later:"
                " run womm template update -I to decide"
            )
            for path in outcome.pending:
                ezprinter.info(f"Pending: {path}")
    if result.store_error:
        ezprinter.error(f"Template updated, store not updated: {result.store_error}")
        ezprinter.info("Run womm template update ID again to refresh the store")
    elif result.entry is not None:
        ezprinter.success(
            f"Store refreshed: {result.entry.qualified_id}"
            f" (v{result.entry.store_version})"
        )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "render_extraction_report",
    "render_template_list",
    "render_template_result",
    "render_update_preview",
    "render_update_result",
]
