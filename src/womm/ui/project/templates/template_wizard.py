#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE WIZARD - Prompts for interactive template commands
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Prompts behind ``womm template add|init|update|remove -I``.

Ctrl+C is left to Click, which aborts the command before anything is written.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Third-party imports
from rich.prompt import Prompt

# Local imports
from ....shared.models.template_source import TemplateEntry
from ...common.prompts import confirm, prompt_choice

# ///////////////////////////////////////////////////////////////
# FUNCTIONS
# ///////////////////////////////////////////////////////////////


def ask_text(message: str, default: str | None = None) -> str:
    """Ask for a non-empty value, offering ``default`` when given.

    Args:
        message: Question shown to the user.
        default: Value used when the user just presses Enter.

    Returns:
        str: The stripped answer.
    """
    while True:
        answer = (
            Prompt.ask(message, default=default) if default else Prompt.ask(message)
        )
        if answer.strip():
            return answer.strip()


def choose_template(entries: list[TemplateEntry], message: str) -> TemplateEntry:
    """Let the user pick one template by its qualified identifier.

    Args:
        entries: Candidate entries, at least one.
        message: Question shown above the list.

    Returns:
        TemplateEntry: The selected entry.
    """
    by_id = {entry.qualified_id: entry for entry in entries}
    return by_id[prompt_choice(message, list(by_id))]


def confirm_action(message: str, *, default: bool = True) -> bool:
    """Ask a yes/no question.

    Args:
        message: Question shown to the user.
        default: Answer used when the user just presses Enter.

    Returns:
        bool: True when the user agrees.
    """
    return confirm(message, default=default)


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["ask_text", "choose_template", "confirm_action"]
