#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# SETUP - Setup Commands
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Setup commands for WOMM CLI.

This module handles configuration of existing projects using the modular architecture.
Provides commands for setting up development environments in existing projects.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

# Third-party imports
import click

# Heavy imports stay in the callbacks: `womm -h` must not load them.
if TYPE_CHECKING:
    from ...interfaces import ProjectManagerInterface

# ///////////////////////////////////////////////////////////////
# COMMAND GROUPS
# ///////////////////////////////////////////////////////////////


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.option(
    "--update",
    "update_tools",
    is_flag=True,
    help="Update official template tooling and reviewed configurations",
)
@click.option(
    "--path",
    "update_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project to update",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Resolve and validate an update without changing the project",
)
@click.option(
    "--allow-destructive-actions",
    is_flag=True,
    help="Allow reviewed block moves and destructive configuration migrations",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
@click.pass_context
def setup_group(
    ctx: click.Context,
    verbose: bool,
    update_tools: bool,
    update_path: Path,
    dry_run: bool,
    allow_destructive_actions: bool,
) -> None:
    """🔧 Configure existing projects with development tools."""
    # Configure verbose mode if requested
    if verbose:
        from ezplog import LogLevel

        from ...ui.common import ezpl

        ezpl.set_level(LogLevel.DEBUG.label)

    update_options = (
        dry_run
        or allow_destructive_actions
        or ctx.get_parameter_source("update_path")
        == click.core.ParameterSource.COMMANDLINE
    )
    if ctx.invoked_subcommand is not None and (update_tools or update_options):
        raise click.UsageError(
            "Update options cannot be combined with a setup subcommand"
        )
    if update_options and not update_tools:
        raise click.UsageError("These options require --update")
    if update_tools:
        from ...interfaces.project.tooling_update_interface import update_tooling
        from ...ui.common import ezprinter
        from ...ui.project.setup.tooling_update_display import print_tooling_update_plan

        def approve(result: Any) -> bool:
            print_tooling_update_plan(result)
            return click.confirm("Apply this tooling update?", default=False)

        result = update_tooling(
            update_path,
            dry_run=dry_run,
            allow_destructive_actions=allow_destructive_actions,
            approve=approve,
        )
        if not result.success:
            raise click.ClickException(result.error)
        if dry_run:
            print_tooling_update_plan(result)
        ezprinter.info(result.message)
        if result.backup_path:
            ezprinter.info(f"Backup: {result.backup_path}")
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ///////////////////////////////////////////////////////////////
# AUTO-DETECTION COMMANDS
# ///////////////////////////////////////////////////////////////


@setup_group.command("detect")
@click.help_option("-h", "--help")
@click.option(
    "-p",
    "--path",
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Path to the project directory",
)
@click.option(
    "-I",
    "--interactive",
    is_flag=True,
    help="Run in interactive mode with guided setup",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
def setup_detect(
    project_path: Path,
    interactive: bool,
    verbose: bool,
) -> None:
    """🔍 Detect the project type and show the setup steps available for it.

    Use -I to run the guided setup on the detected type.
    """
    from ezplog import LogLevel

    from ...interfaces import ProjectManagerInterface
    from ...services.project.setup_profile_resolver import list_setup_identifiers
    from ...ui.common import ezpl, ezprinter

    # Configure verbose mode if requested
    if verbose:
        ezpl.set_level(LogLevel.DEBUG.label)

    # Initialize project manager (lazy loading)
    project_manager = ProjectManagerInterface()

    try:
        # Detect project type using ProjectManagerInterface
        detection_result = project_manager.detect_project_type(project_path)
        detected_type = detection_result.project_type
        confidence = detection_result.confidence

        if detected_type == "unknown" or not detected_type:
            if not detection_result.success and detection_result.error:
                ezprinter.error(
                    f"Error detecting project type: {detection_result.error}"
                )
            else:
                ezprinter.error(
                    "No suitable project type detected in the specified directory"
                )
                known = ", ".join(
                    identifier for identifier, _description in list_setup_identifiers()
                )
                ezprinter.info(f"Supported project types: {known}")
            sys.exit(1)

        ezprinter.success(
            f"Detected project type: {detected_type} (confidence: {confidence}%)"
        )

        # Interactive mode
        if interactive:
            success = _run_interactive_setup(
                project_manager, detected_type, project_path
            )
            if not success:
                sys.exit(1)
            return

        # Non-interactive mode
        options: dict[str, Any] = {}
        success = _run_direct_setup(
            project_manager, detected_type, project_path, options
        )
        if not success:
            sys.exit(1)
        return

    except Exception as e:
        ezprinter.error(f"Error detecting project type: {e}")
        sys.exit(1)


# ///////////////////////////////////////////////////////////////
# PYTHON PROJECT COMMANDS
# ///////////////////////////////////////////////////////////////


@setup_group.command("python")
@click.help_option("-h", "--help")
@click.option(
    "-p",
    "--path",
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Path to the Python project directory",
)
@click.option(
    "-I",
    "--interactive",
    is_flag=True,
    help="Run in interactive mode with guided setup",
)
@click.option(
    "--virtual-env",
    is_flag=True,
    help="Create virtual environment",
)
@click.option(
    "--install-deps",
    is_flag=True,
    help="Install dependencies, development ones included",
)
@click.option(
    "--setup-git-hooks",
    is_flag=True,
    help="Initialize the Git repository and install its pre-commit hooks",
)
@click.option(
    "--setup-vscode",
    is_flag=True,
    help="Write the VS Code settings and recommended extensions",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
def setup_python(
    project_path: Path,
    interactive: bool,
    virtual_env: bool,
    install_deps: bool,
    setup_git_hooks: bool,
    setup_vscode: bool,
    verbose: bool,
) -> None:
    """🐍 Configure existing Python project with development environment.

    Every step is opt-in: pass the flags of the steps to run. Without any,
    the project is only checked and nothing is written.
    """
    from ezplog import LogLevel

    from ...interfaces import ProjectManagerInterface
    from ...ui.common import ezpl, ezprinter

    # Configure verbose mode if requested
    if verbose:
        ezpl.set_level(LogLevel.DEBUG.label)

    # Initialize project manager
    project_manager = ProjectManagerInterface()

    try:
        # Interactive mode
        if interactive:
            success = _run_interactive_setup(project_manager, "python", project_path)
            if not success:
                sys.exit(1)
            return

        # Non-interactive mode
        options = {
            "virtual_env": virtual_env,
            "install_deps": install_deps,
            "setup_git_hooks": setup_git_hooks,
            "setup_vscode": setup_vscode,
        }
        success = _run_direct_setup(project_manager, "python", project_path, options)
        if not success:
            sys.exit(1)
        return

    except Exception as e:
        ezprinter.error(f"Error configuring Python project: {e}")
        sys.exit(1)


# ///////////////////////////////////////////////////////////////
# JAVASCRIPT PROJECT COMMANDS
# ///////////////////////////////////////////////////////////////


@setup_group.command("javascript")
@click.help_option("-h", "--help")
@click.option(
    "-p",
    "--path",
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Path to the JavaScript project directory",
)
@click.option(
    "-t",
    "--type",
    "project_type",
    type=click.Choice(["javascript", "react", "vue"]),
    help="JavaScript project type (auto-detected if not specified)",
)
@click.option(
    "-I",
    "--interactive",
    is_flag=True,
    help="Run in interactive mode with guided setup",
)
@click.option(
    "--install-deps",
    is_flag=True,
    help="Install dependencies, devDependencies included",
)
@click.option(
    "--setup-git-hooks",
    is_flag=True,
    help="Initialize the Git repository",
)
@click.option(
    "--setup-vscode",
    is_flag=True,
    help="Write the VS Code settings and recommended extensions",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
def setup_javascript(
    project_path: Path,
    project_type: str | None,
    interactive: bool,
    install_deps: bool,
    setup_git_hooks: bool,
    setup_vscode: bool,
    verbose: bool,
) -> None:
    """🟨 Configure existing JavaScript project with development environment.

    Every step is opt-in: pass the flags of the steps to run. Without any,
    the project is only checked and nothing is written.
    """
    from ezplog import LogLevel

    from ...interfaces import ProjectManagerInterface
    from ...ui.common import ezpl, ezprinter

    # Configure verbose mode if requested
    if verbose:
        ezpl.set_level(LogLevel.DEBUG.label)

    # Initialize project manager
    project_manager = ProjectManagerInterface()

    try:
        # Auto-detect type if not specified
        if not project_type:
            detection_result = project_manager.detect_project_type(project_path)
            detected_type = detection_result.project_type
            confidence = detection_result.confidence
            if detected_type in ["javascript", "react", "vue"]:
                project_type = detected_type
                ezprinter.info(
                    f"Auto-detected project type: {project_type} (confidence: {confidence}%)"
                )
            else:
                ezprinter.error("Could not auto-detect JavaScript project type")
                ezprinter.info("Please specify --type (javascript, react, vue)")
                sys.exit(1)

        if not project_type:
            ezprinter.error("Project type is required for setup")
            sys.exit(1)
        project_type_value = cast(str, project_type)

        # Interactive mode
        if interactive:
            success = _run_interactive_setup(
                project_manager, project_type_value, project_path
            )
            if not success:
                sys.exit(1)
            return

        # Non-interactive mode
        options = {
            "install_deps": install_deps,
            "setup_git_hooks": setup_git_hooks,
            "setup_vscode": setup_vscode,
        }
        success = _run_direct_setup(
            project_manager, project_type_value, project_path, options
        )
        if not success:
            sys.exit(1)
        return

    except Exception as e:
        ezprinter.error(f"Error configuring JavaScript project: {e}")
        sys.exit(1)


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS - INTERACTIVE MODES
# ///////////////////////////////////////////////////////////////


def _run_interactive_setup(
    project_manager: ProjectManagerInterface, project_type: str, project_path: Path
) -> bool:
    """Run interactive project setup."""
    from ...ui.common import ezprinter
    from ...ui.project import ProjectWizard

    # Get setup configuration
    config = ProjectWizard.run_interactive_setup_for_existing_project(
        project_type, project_path
    )
    if not config:
        ezprinter.error("Project setup cancelled")
        return False

    # Configure project
    options = config.get("options", {})
    if not isinstance(options, dict):
        ezprinter.error("Invalid options returned by wizard")
        return False

    return _setup_and_report(project_manager, project_type, project_path, options)


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS - DIRECT MODES
# ///////////////////////////////////////////////////////////////


def _run_direct_setup(
    project_manager: ProjectManagerInterface,
    project_type: str,
    project_path: Path,
    options: dict[str, Any] | None = None,
) -> bool:
    """Run direct project setup."""
    return _setup_and_report(project_manager, project_type, project_path, options or {})


def _setup_and_report(
    project_manager: ProjectManagerInterface,
    project_type: str,
    project_path: Path,
    options: dict[str, Any],
) -> bool:
    """Run the requested setup steps, or point to their flags when none is."""
    from ...services.project.setup_profile_resolver import resolve_setup_profile
    from ...ui.common import ezprinter
    from ...ui.project import print_project_setup_result, print_setup_steps_hint

    def _coerce_bool(value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    steps = {
        name: _coerce_bool(options.get(name, False))
        for name in ("virtual_env", "install_deps", "setup_git_hooks", "setup_vscode")
    }

    # With no step, setup_project only checks the project: nothing is written.
    result = project_manager.setup_project(
        project_type=project_type, project_path=project_path, **steps
    )

    if not result.success:
        ezprinter.error(f"Failed to configure {project_type} project: {result.error}")
        return False
    if any(steps.values()):
        print_project_setup_result(result)
    else:
        profile = resolve_setup_profile(project_type)
        language = profile.language if profile else "javascript"
        print_setup_steps_hint(language, project_path)
    return True
