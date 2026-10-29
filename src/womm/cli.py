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
from .ui.common import ezprinter

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
# MAIN CLI FUNCTION
# ///////////////////////////////////////////////////////////////


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.version_option(version=__version__)
@click.pass_context
def womm(ctx: click.Context) -> None:
    """🛠️ Works On My Machine - Universal development tools."""
    if ctx.invoked_subcommand is None:
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
