#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# SETUP SUMMARIES - Project Setup Completion Summaries
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Setup completion summaries for existing projects.

This module provides UI components for displaying completion summaries
after setting up existing projects, following the established patterns in the WOMM codebase.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
from pathlib import Path

# Third-party imports
from rich.panel import Panel

# Local imports
from ....shared.results import ProjectSetupResult
from ...common.logging import ezconsole, ezprinter

# ///////////////////////////////////////////////////////////////
# FUNCTIONS
# ///////////////////////////////////////////////////////////////


def print_setup_completion_summary(
    project_path: Path,
    project_type: str,
    virtual_env: bool = False,
    install_deps: bool = False,
    setup_dev_tools: bool = False,
    setup_git_hooks: bool = False,
) -> None:
    """
    Print a completion summary for project setup.

    Args:
        project_path: Path to the project
        project_type: Type of project (python, javascript, react, vue)
        virtual_env: Whether virtual environment was set up
        install_deps: Whether dependencies were installed
        setup_dev_tools: Whether development tools were configured
        setup_git_hooks: Whether Git hooks were set up
    """
    completed = [
        label
        for enabled, label in (
            (virtual_env, "Virtual environment setup"),
            (install_deps, "Dependencies installed"),
            (setup_dev_tools, "Development tools configured"),
            (setup_git_hooks, "Git hooks configured"),
        )
        if enabled
    ]
    content = f"📁 Project location: {project_path}\n📋 Project type: {project_type}"
    if completed:
        content += "\n\n🔧 Configuration completed:\n"
        content += "\n".join(f"  • {label}" for label in completed)

    content += "\n\n🚀 Next steps:\n"
    if (project_path / "README.md").is_file():
        content += "Read the project's README.md for setup and usage instructions.\n"
    content += "Check the project configuration for available development commands."

    title = {
        "python": "🔧 Python Project Setup Completed!",
        "javascript": "🔧 JavaScript Project Setup Completed!",
        "node": "🔧 JavaScript Project Setup Completed!",
        "react": "🔧 JavaScript Project Setup Completed!",
        "vue": "🔧 JavaScript Project Setup Completed!",
    }.get(project_type, "🔧 Project Setup Completed!")
    ezconsole.print("")
    ezconsole.print(
        Panel(
            content, title=title, border_style="bright_blue", width=80, padding=(1, 1)
        )
    )


def print_project_setup_result(result: ProjectSetupResult) -> None:
    """Render a successful project-setup result for the CLI."""
    project_path = result.project_path
    if project_path is None:
        return

    configured_tools = result.tools_configured or []
    print_setup_completion_summary(
        project_path,
        result.project_type,
        virtual_env="venv" in configured_tools,
        install_deps="dependencies" in configured_tools,
        setup_dev_tools="dev_tools" in configured_tools,
        setup_git_hooks="git_hooks" in configured_tools,
    )
    for warning in result.warnings or []:
        ezprinter.warning(warning)


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["print_project_setup_result", "print_setup_completion_summary"]
