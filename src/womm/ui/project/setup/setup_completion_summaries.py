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
# CONSTANTS
# ///////////////////////////////////////////////////////////////

# Step flags of `womm setup <language>`; a test keeps them in sync with the CLI.
SETUP_STEP_FLAGS: dict[str, tuple[tuple[str, str], ...]] = {
    "python": (
        ("--virtual-env", "Create the virtual environment"),
        ("--install-deps", "Install the dependencies, dev ones included"),
        ("--setup-git-hooks", "Initialize Git and install the pre-commit hooks"),
        ("--setup-vscode", "Write the VS Code settings and extensions"),
    ),
    "javascript": (
        ("--install-deps", "Install the dependencies, devDependencies included"),
        ("--setup-git-hooks", "Initialize the Git repository"),
        ("--setup-vscode", "Write the VS Code settings and extensions"),
    ),
}

# ///////////////////////////////////////////////////////////////
# FUNCTIONS
# ///////////////////////////////////////////////////////////////


def print_setup_completion_summary(
    project_path: Path,
    project_type: str,
    virtual_env: bool = False,
    install_deps: bool = False,
    git_repository: bool = False,
    setup_git_hooks: bool = False,
    vscode: bool = False,
    warning_count: int = 0,
) -> None:
    """
    Print a completion summary for project setup.

    Args:
        project_path: Path to the project
        project_type: Type of project (python, javascript, react, vue)
        virtual_env: Whether virtual environment was set up
        install_deps: Whether dependencies were installed
        git_repository: Whether the Git repository was initialized
        setup_git_hooks: Whether Git hooks were installed
        vscode: Whether the VS Code configuration was written
        warning_count: Number of warnings, each about a step that did not complete
    """
    completed = [
        label
        for enabled, label in (
            (virtual_env, "Virtual environment setup"),
            (install_deps, "Dependencies installed"),
            (git_repository, "Git repository initialized"),
            (setup_git_hooks, "Git hooks installed"),
            (vscode, "VS Code configuration written"),
        )
        if enabled
    ]
    content = f"📁 Project location: {project_path}\n📋 Project type: {project_type}"
    if completed:
        content += "\n\n🔧 Configuration completed:\n"
        content += "\n".join(f"  • {label}" for label in completed)
    if warning_count:
        content += (
            f"\n\n⚠️  Some steps did not complete ({warning_count} warning(s) "
            "below): fix the cause, then run the setup again."
        )

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
    border_style = "bright_blue"
    if warning_count:
        title = title.replace("Completed!", "Incomplete")
        border_style = "yellow"
    ezconsole.print("")
    ezconsole.print(
        Panel(content, title=title, border_style=border_style, width=80, padding=(1, 1))
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
        git_repository="git" in configured_tools,
        setup_git_hooks="git_hooks" in configured_tools,
        vscode="vscode" in configured_tools,
        warning_count=len(result.warnings or []),
    )
    for warning in result.warnings or []:
        ezprinter.warning(warning)


def print_setup_steps_hint(language: str, project_path: Path) -> None:
    """Tell the user that no step ran, and which flags select them.

    Args:
        language: Language family of the project ("python" or "javascript")
        project_path: Path to the project
    """
    flags = SETUP_STEP_FLAGS.get(language, SETUP_STEP_FLAGS["javascript"])
    command = f"womm setup {language}"
    if project_path.resolve() != Path.cwd().resolve():
        command += f' -p "{project_path}"'
    width = max(len(flag) for flag, _description in flags)
    content = "No setup step requested: nothing was changed.\n\n"
    content += "🔧 Choose the steps to run:\n"
    content += "\n".join(
        f"  {flag:<{width}}  {description}" for flag, description in flags
    )
    content += "\n\n🚀 For example, all of them:\n"
    content += f"  {command} " + " ".join(flag for flag, _description in flags)
    content += f"\n\nGuided mode: {command} -I"

    ezconsole.print("")
    ezconsole.print(
        Panel(
            content,
            title="🔧 No Setup Step Requested",
            border_style="bright_blue",
            width=80,
            padding=(1, 1),
        )
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "SETUP_STEP_FLAGS",
    "print_project_setup_result",
    "print_setup_completion_summary",
    "print_setup_steps_hint",
]
