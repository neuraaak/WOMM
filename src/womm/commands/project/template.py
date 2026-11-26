#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE - Template Catalog Commands
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Template catalog commands for WOMM CLI.

This module manages the Copier template catalog: listing, showing, adding,
removing and updating entries. Rendering is delegated to Copier itself
(see ``womm create``) — this vertical is catalog CRUD only.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
from pathlib import Path

# Third-party imports
import click

# Local imports
from .create import parse_data_options

# Heavy imports stay in the callbacks: `womm -h` must not load them.

# ///////////////////////////////////////////////////////////////
# COMMAND GROUP
# ///////////////////////////////////////////////////////////////


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.pass_context
def template_group(ctx: click.Context) -> None:
    """Manage the Copier template catalog."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ///////////////////////////////////////////////////////////////
# COMMANDS
# ///////////////////////////////////////////////////////////////


@template_group.command("list")
@click.help_option("-h", "--help")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_list(verbose: bool) -> None:
    """List every known template."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import render_template_list

    result = TemplateStoreInterface().list_templates()
    render_template_list(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("show", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_show(identifier: str, verbose: bool) -> None:
    """Show a single catalog entry."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import render_template_result

    result = TemplateStoreInterface().show_template(identifier)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("add", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_add(identifier: str, source: Path, verbose: bool) -> None:
    """Register a local template under the user namespace."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import render_template_result

    result = TemplateStoreInterface().add_template(identifier, source)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("remove", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_remove(identifier: str, verbose: bool) -> None:
    """Unregister a user template."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import render_template_result

    result = TemplateStoreInterface().remove_template(identifier)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("update", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_update(identifier: str, source: Path, verbose: bool) -> None:
    """Point an existing user template at a new source."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import render_template_result

    result = TemplateStoreInterface().update_template(identifier, source)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("init", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("destination", type=click.Path(path_type=Path))
@click.option(
    "--data",
    "data",
    multiple=True,
    metavar="KEY=VALUE",
    help="Pre-fill a meta-template answer. Repeatable.",
)
@click.option(
    "--defaults",
    is_flag=True,
    help="Use meta-template defaults instead of prompting.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Scaffold into a non-empty destination.",
)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_init(
    destination: Path,
    data: tuple[str, ...],
    defaults: bool,
    force: bool,
    verbose: bool,
) -> None:
    """Scaffold a new Copier template skeleton."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import render_project_creation_result

    answers = parse_data_options(data)
    result = TemplateStoreInterface().init_template(
        destination,
        answers=answers,
        force=force,
        defaults=defaults,
    )
    render_project_creation_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["template_group"]
