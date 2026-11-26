#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# SETUP PROFILE RESOLVER - Generic project-type resolution for setup
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Resolve a project-type identifier to a setup profile.

Replaces the historical fixed ``SUPPORTED_PROJECT_TYPES`` list. An
identifier is looked up in the template catalog first (``_womm.setup``
metadata); ``react``/``vue`` are not yet separate catalog entries so they
fall back to a small static alias table.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .template_store_service import TemplateStoreService

# ///////////////////////////////////////////////////////////////
# MODELS
# ///////////////////////////////////////////////////////////////


@dataclass(frozen=True)
class SetupProfile:
    """What `womm setup` needs to know about a project type.

    Attributes:
        language: Language family selecting the environment service
            ("python" or "javascript").
        template_source: Copier template used to render the VS Code settings.
        answers: Template answers needed to render the settings.
    """

    language: str
    template_source: Path
    answers: Mapping[str, object]


# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

# Identifiers not yet backed by a separate catalog entry. Only reachable
# via explicit --type or the interactive wizard: auto-detection never
# returns them (see ProjectDetectionService.detect_project_type).
_LEGACY_SETUP_ALIASES: dict[str, tuple[str, str]] = {
    "react": ("react", "React.js project (javascript template variant)"),
    "vue": ("vue", "Vue.js project (javascript template variant)"),
}

# ///////////////////////////////////////////////////////////////
# PUBLIC FUNCTIONS
# ///////////////////////////////////////////////////////////////


def resolve_setup_profile(
    identifier: str, store: TemplateStoreService | None = None
) -> SetupProfile | None:
    """Resolve an identifier to a setup profile.

    Args:
        identifier: Catalog id, short or qualified (e.g. "python",
            "user/mytpl"), or legacy alias (e.g. "react").
        store: Template store to query. Defaults to a fresh
            ``TemplateStoreService``.

    Returns:
        SetupProfile | None: The resolved profile, or ``None`` when the
        identifier is neither a catalog entry with setup metadata nor a
        known legacy alias.
    """
    store = store or TemplateStoreService()
    entries = store.list_templates()
    for entry in entries:
        if identifier in (entry.id, entry.qualified_id) and entry.setup_language:
            return SetupProfile(
                language=entry.setup_language,
                template_source=entry.source,
                answers=_setup_answers(),
            )

    alias = _LEGACY_SETUP_ALIASES.get(identifier)
    if alias is None:
        return None
    javascript_template = next(
        (entry for entry in entries if entry.id == "javascript"), None
    )
    if javascript_template is None:
        return None
    return SetupProfile(
        language="javascript",
        template_source=javascript_template.source,
        answers={**_setup_answers(), "framework": alias[0]},
    )


def _setup_answers() -> dict[str, object]:
    """Supply non-interactive answers needed to render setup configuration."""
    return {
        "description": "Project configured by WOMM",
        "with_vscode": True,
    }


def list_setup_identifiers(
    store: TemplateStoreService | None = None,
) -> list[tuple[str, str]]:
    """List every identifier `womm setup` accepts, with a description.

    Args:
        store: Template store to query. Defaults to a fresh
            ``TemplateStoreService``.

    Returns:
        list[tuple[str, str]]: ``(identifier, description)`` pairs, catalog
        entries first (sorted by id), then legacy aliases.
    """
    store = store or TemplateStoreService()
    catalog = sorted(
        (
            (entry.id, entry.description)
            for entry in store.list_templates()
            if entry.setup_language
        ),
        key=lambda pair: pair[0],
    )
    aliases = [
        (identifier, description)
        for identifier, (_framework, description) in _LEGACY_SETUP_ALIASES.items()
    ]
    return catalog + aliases


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["SetupProfile", "list_setup_identifiers", "resolve_setup_profile"]
