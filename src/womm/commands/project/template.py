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
from typing import TYPE_CHECKING

# Third-party imports
import click

# Local imports
from .create import parse_data_options

# Heavy imports stay in the callbacks: `womm -h` must not load them.
if TYPE_CHECKING:
    from ...interfaces.project.template_store_interface import (
        TemplateStoreInterface,
    )

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


INTERACTIVE_HELP = "Ask for missing arguments and confirm before writing."


@template_group.command("add", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier", required=False)
@click.argument("source", type=click.Path(path_type=Path), required=False)
@click.option("-I", "--interactive", is_flag=True, help=INTERACTIVE_HELP)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_add(
    identifier: str | None, source: Path | None, interactive: bool, verbose: bool
) -> None:
    """Register a local template under the user namespace."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.common import ezprinter
    from ...ui.project import ask_text, confirm_action, render_template_result

    store = TemplateStoreInterface()
    if interactive:
        identifier = identifier or ask_text("Template identifier")
        source = source or Path(ask_text("Template directory"))
        preview = store.preview_template(identifier, source)
        render_template_result(preview, verbose=True)
        if not preview.success or preview.entry is None:
            raise SystemExit(1)
        if not confirm_action(f"Register {preview.entry.qualified_id}?"):
            ezprinter.info("Cancelled, nothing was registered")
            return
    identifier = _require(identifier, "IDENTIFIER")
    source = _require(source, "SOURCE")

    result = store.add_template(identifier, source)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("remove", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier", required=False)
@click.option("-I", "--interactive", is_flag=True, help=INTERACTIVE_HELP)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_remove(identifier: str | None, interactive: bool, verbose: bool) -> None:
    """Unregister a user template."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.common import ezprinter
    from ...ui.project import confirm_action, render_template_result

    store = TemplateStoreInterface()
    if interactive:
        identifier = identifier or _pick_user_template(store, "Template to remove")
        if not confirm_action(
            f"Unregister {identifier}? Its directory stays on disk.", default=False
        ):
            ezprinter.info("Cancelled, nothing was removed")
            return
    identifier = _require(identifier, "IDENTIFIER")

    result = store.remove_template(identifier)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("update", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("identifier", required=False)
@click.argument("source", type=click.Path(path_type=Path), required=False)
@click.option("-I", "--interactive", is_flag=True, help=INTERACTIVE_HELP)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_update(
    identifier: str | None, source: Path | None, interactive: bool, verbose: bool
) -> None:
    """Refresh WOMM's copy of a user template, or copy it from SOURCE.

    Without SOURCE, the copy is refreshed from the directory it was made from.
    """
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.common import ezprinter
    from ...ui.project import ask_text, confirm_action, render_template_result

    store = TemplateStoreInterface()
    if interactive:
        identifier = identifier or _pick_user_template(store, "Template to update")
        current = store.show_template(identifier)
        if not current.success or current.entry is None:
            render_template_result(current)
            raise SystemExit(1)
        origin = current.entry.copied_from or current.entry.source
        source = source or Path(ask_text("Copy it from", default=str(origin)))
        if not confirm_action(f"Copy {current.entry.qualified_id} from {source}?"):
            ezprinter.info("Cancelled, nothing was updated")
            return
    identifier = _require(identifier, "IDENTIFIER")

    result = store.update_template(identifier, source)
    render_template_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)


@template_group.command("init", no_args_is_help=True)
@click.help_option("-h", "--help")
@click.argument("destination", type=click.Path(path_type=Path), required=False)
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
@click.option(
    "-I",
    "--interactive",
    is_flag=True,
    help="Ask for the destination, then offer to register the skeleton.",
)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output.")
def template_init(
    destination: Path | None,
    data: tuple[str, ...],
    defaults: bool,
    force: bool,
    interactive: bool,
    verbose: bool,
) -> None:
    """Scaffold a new Copier template skeleton."""
    from ...interfaces.project.template_store_interface import TemplateStoreInterface
    from ...ui.project import (
        ask_text,
        confirm_action,
        render_project_creation_result,
        render_template_result,
    )

    answers = parse_data_options(data)
    if interactive and destination is None:
        destination = Path(ask_text("Template destination"))
    destination = _require(destination, "DESTINATION")

    store = TemplateStoreInterface()
    result = store.init_template(
        destination,
        answers=answers,
        force=force,
        defaults=defaults,
    )
    render_project_creation_result(result, verbose=verbose)
    if not result.success:
        raise SystemExit(1)

    if interactive and confirm_action("Register this template in the catalog?"):
        identifier = ask_text("Template identifier", default=destination.name)
        added = store.add_template(identifier, destination)
        render_template_result(added, verbose=verbose)
        if not added.success:
            raise SystemExit(1)


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS
# ///////////////////////////////////////////////////////////////


def _require[T](value: T | None, name: str) -> T:
    """Fail like a missing Click argument when ``-I`` did not supply it."""
    if value is None:
        raise click.UsageError(f"Missing argument '{name}'. Pass it, or use -I.")
    return value


def _pick_user_template(store: TemplateStoreInterface, message: str) -> str:
    """Let the user pick a registered user template; exit when there is none."""
    from ...shared.models.template_source import TemplateOrigin
    from ...ui.common import ezprinter
    from ...ui.project import choose_template, render_template_list

    listing = store.list_templates()
    if not listing.success:
        render_template_list(listing)
        raise SystemExit(1)
    entries = [e for e in listing.entries or [] if e.origin is TemplateOrigin.USER]
    if not entries:
        ezprinter.error("No user template registered")
        raise SystemExit(1)
    return choose_template(entries, message).qualified_id


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["template_group"]
