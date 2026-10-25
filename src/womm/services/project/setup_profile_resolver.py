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
from dataclasses import dataclass

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
        vscode_variant: VS Code asset variant to copy (e.g. "py", "js",
            "react", "vue").
    """

    language: str
    vscode_variant: str


# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

# Identifiers not yet backed by a separate catalog entry. Only reachable
# via explicit --type or the interactive wizard: auto-detection never
# returns them (see ProjectDetectionService.detect_project_type).
_LEGACY_SETUP_ALIASES: dict[str, tuple[SetupProfile, str]] = {
    "react": (
        SetupProfile(language="javascript", vscode_variant="react"),
        "React.js project (javascript template variant)",
    ),
    "vue": (
        SetupProfile(language="javascript", vscode_variant="vue"),
        "Vue.js project (javascript template variant)",
    ),
}

# ///////////////////////////////////////////////////////////////
# PUBLIC FUNCTIONS
# ///////////////////////////////////////////////////////////////


def resolve_setup_profile(
    identifier: str, store: TemplateStoreService | None = None
) -> SetupProfile | None:
    """Resolve an identifier to a setup profile.

    Args:
        identifier: Catalog id (e.g. "python") or legacy alias
            (e.g. "react").
        store: Template store to query. Defaults to a fresh
            ``TemplateStoreService``.

    Returns:
        SetupProfile | None: The resolved profile, or ``None`` when the
        identifier is neither a catalog entry with setup metadata nor a
        known legacy alias.
    """
    store = store or TemplateStoreService()
    for entry in store.list_templates():
        if entry.id == identifier and entry.setup_language:
            return SetupProfile(
                language=entry.setup_language,
                vscode_variant=entry.setup_vscode_variant,
            )

    alias = _LEGACY_SETUP_ALIASES.get(identifier)
    return alias[0] if alias else None


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
        for identifier, (_profile, description) in _LEGACY_SETUP_ALIASES.items()
    ]
    return catalog + aliases


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["SetupProfile", "list_setup_identifiers", "resolve_setup_profile"]
