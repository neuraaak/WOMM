#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# LOGGING - ezplog integration and WOMM Rich helpers
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
ezplog integration for Works On My Machine.

This module configures ezplog and extends its printer with the Rich object
builders that are specific to WOMM.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
from typing import Any, cast

# Third-party imports
from ezplog import EzLogger, Ezpl, EzPrinter, RichWizard
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Local imports
from ...shared.configs.logging_config import LoggingConfig

# ///////////////////////////////////////////////////////////////
# EXTENDED PRINTER CLASS
# ///////////////////////////////////////////////////////////////


class WommPrinter(EzPrinter):
    """EzPrinter extended with WOMM-specific Rich object builders."""

    @property
    def console(self) -> Console:
        """Expose the Rich console until ezplog provides a public accessor."""
        return self._console

    def print_header(self, title: str, **kwargs: Any) -> None:
        """Display a WOMM command header with separators."""
        self._console.print(":" * 80, style="dim black", **kwargs)
        self._console.print(
            f"** {title} **",
            style="bold black",
            justify="center",
            width=80,
            **kwargs,
        )
        self._console.print(":" * 80, style="dim black", **kwargs)
        self._console.print("")

    def create_panel(
        self,
        content: Any,
        title: str | None = None,
        border_style: str = "blue",
        width: int = 80,
        **kwargs: Any,
    ) -> Panel:
        """Build a generic WOMM panel without displaying it."""
        return Panel(
            content,
            title=title,
            border_style=border_style,
            width=width,
            **kwargs,
        )

    def create_info_panel(
        self,
        title: str,
        content: str,
        style: str = "cyan",
        border_style: str = "cyan",
        width: int = 80,
        **kwargs: Any,
    ) -> Panel:
        """Build a WOMM information panel without displaying it."""
        text = Text(content, style=style)
        return Panel(
            Align(text, align="left"),
            title=f"ℹ️ {title}",
            border_style=border_style,
            width=width,
            **kwargs,
        )

    def create_table(
        self,
        title: str,
        columns: list[str] | list[tuple[str, str | None, bool]],
        rows: list[list[Any]] | None = None,
        show_header: bool = True,
        **kwargs: Any,
    ) -> Table:
        """Build a WOMM table without displaying it."""
        table = Table(title=title, show_header=show_header, **kwargs)

        for column in columns:
            if isinstance(column, tuple):
                name, style, no_wrap = column
                table.add_column(name, style=style or "cyan", no_wrap=no_wrap)
            else:
                table.add_column(column, style="cyan", no_wrap=True)

        if rows:
            for row in rows:
                table.add_row(*[str(cell) for cell in row])

        return table

    def create_backup_table(self, backups: list[dict[str, Any]]) -> Table:
        """Build the table used to display PATH backup metadata."""
        table = Table(title="PATH Backups", show_header=True)
        table.add_column("Backup File", style="cyan", no_wrap=True)
        table.add_column("Size", style="green", no_wrap=True)
        table.add_column("Modified", style="yellow", no_wrap=True)
        table.add_column("Description", style="white")

        for backup in backups:
            size = backup.get("size", 0)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024} KB"
            else:
                size_str = f"{size // (1024 * 1024)} MB"

            description = backup.get("description", "No description")
            if len(description) > 50:
                description = description[:47] + "..."

            table.add_row(
                backup.get("name", ""),
                size_str,
                backup.get("modified", ""),
                description,
            )

        return table


# ///////////////////////////////////////////////////////////////
# GLOBAL INSTANCE
# ///////////////////////////////////////////////////////////////

log_folder = LoggingConfig.get_log_dir()
log_folder.mkdir(parents=True, exist_ok=True)
first_init = not Ezpl.is_initialized()
ezpl = Ezpl(
    log_file=LoggingConfig.get_log_file(),
    log_level=LoggingConfig.DEFAULT_LEVEL,
    log_rotation=LoggingConfig.ROTATION,
    log_retention=LoggingConfig.RETENTION,
    log_compression=LoggingConfig.COMPRESSION,
)
if first_init:
    ezpl.set_printer_class(WommPrinter)
    ezpl.lock_config()

ezprinter = cast(WommPrinter, ezpl.get_printer())
ezlogger: EzLogger = ezpl.get_logger()
ezconsole: Console = ezprinter.console
ezwizard = RichWizard(ezconsole)

# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "WommPrinter",
    "ezconsole",
    "ezlogger",
    "ezpl",
    "ezprinter",
    "ezwizard",
]
