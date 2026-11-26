#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# WOMM CLI - Main CLI Entry Point
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Click entry point for Works On My Machine."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import os
import sys

# Third-party imports
import click

# Local imports
from ._version import __version__
from .commands.core import doctor_cmd, path_group
from .commands.project import create_command, setup_group, template_group
from .commands.system import context_group, deps_group, system_group

# ///////////////////////////////////////////////////////////////
# CONSOLE CONFIGURATION
# ///////////////////////////////////////////////////////////////


def _configure_windows_console() -> None:
    """Configure existing Windows console streams for UTF-8 output."""
    if sys.platform != "win32":
        return

    os.environ["PYTHONIOENCODING"] = "utf-8"
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


_configure_windows_console()


# ///////////////////////////////////////////////////////////////
# UPDATE NOTICE
# ///////////////////////////////////////////////////////////////

# Any non-empty value turns the PyPI release check off.
NO_UPDATE_CHECK_ENV = "WOMM_NO_UPDATE_CHECK"


def _update_check_enabled() -> bool:
    """Check for releases only for a person at a terminal, never in CI."""
    if os.environ.get(NO_UPDATE_CHECK_ENV) or os.environ.get("CI"):
        return False
    return sys.stderr.isatty()


def _report_update() -> None:
    """Print a one-line notice on stderr when a newer release exists."""
    # Imported here: deciding whether to check must cost nothing.
    from .services.system.update_service import check_for_update

    update = check_for_update(__version__)
    if update is not None:
        click.secho(
            f"\nWOMM {update.latest} is available (installed: {update.current})."
            f" Upgrade with: {update.upgrade_command}",
            fg="yellow",
            err=True,
        )


def _version_status() -> tuple[str, str]:
    """Describe, for the welcome screen, whether WOMM is up to date.

    Returns:
        tuple[str, str]: The text to show and its color.
    """
    if not _update_check_enabled():
        return f"WOMM {__version__} (update check skipped).", "cyan"

    from .services.system.update_service import (
        is_newer,
        latest_release,
        upgrade_command,
    )

    latest = latest_release()
    if latest is None:
        return (
            f"WOMM {__version__}. PyPI could not be reached to check for updates.",
            "yellow",
        )
    if is_newer(latest, __version__):
        return (
            f"WOMM {latest} is available (installed: {__version__}).\n"
            f"Upgrade with: {upgrade_command()}",
            "yellow",
        )
    return f"WOMM {__version__} is up to date.", "green"


# ///////////////////////////////////////////////////////////////
# MAIN CLI FUNCTION
# ///////////////////////////////////////////////////////////////


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.version_option(version=__version__)
@click.pass_context
def womm(ctx: click.Context) -> None:
    """🛠️ Works On My Machine - Universal development tools."""
    if ctx.invoked_subcommand is not None:
        if _update_check_enabled():
            # Runs once the command is done, failed runs included.
            ctx.call_on_close(_report_update)
    else:
        # Imported here: the logger setup must not slow down `--version`/`-h`.
        from .ui.common import ezprinter

        ezprinter.console.print(r"""
================================================================================
                    __      _____  __  __ __  __
                    \ \    / / _ \|  \/  |  \/  |
                     \ \/\/ / (_) | |\/| | |\/| |
                      \_/\_/ \___/|_|  |_|_|  |_|
================================================================================


""")
        panel = ezprinter.create_info_panel(
            "Welcome",
            "\n".join(
                [
                    "Universal development tools for Python and JavaScript projects.",
                    "",
                    "Features:",
                    "• Cross-platform project setup and configuration",
                    "• Security validation and safe execution",
                    "• Beautiful terminal interface with Rich",
                    "• Global command access",
                ]
            ),
        )
        ezprinter.console.print(panel)

        status, color = _version_status()
        ezprinter.console.print(
            ezprinter.create_info_panel(
                "Version", status, style=color, border_style=color
            )
        )


# ///////////////////////////////////////////////////////////////
# COMMAND REGISTRATION
# ///////////////////////////////////////////////////////////////


for command in (
    doctor_cmd,
    path_group,
    create_command,
    system_group,
    context_group,
    setup_group,
    template_group,
    deps_group,
):
    womm.add_command(command)


def main() -> None:
    """Run the WOMM command-line interface."""
    womm()


if __name__ == "__main__":
    main()
