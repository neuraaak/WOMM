#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE SOURCE - Template catalog entry model
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Immutable model describing a Copier template known to WOMM."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# ///////////////////////////////////////////////////////////////
# MODELS
# ///////////////////////////////////////////////////////////////


class TemplateOrigin(StrEnum):
    """Where a template comes from.

    Official templates ship inside the wheel and are read-only. User
    templates are registered by the user and stored in the catalog.
    """

    OFFICIAL = "official"
    USER = "user"


@dataclass(frozen=True)
class TemplateEntry:
    """A Copier template known to WOMM.

    Attributes:
        id: Short identifier, unique within an origin (e.g. "python").
        origin: Whether the template ships with WOMM or was registered.
        source: Absolute path to the template root holding ``copier.yml``.
        version: Declared template version, empty when unknown.
        description: One-line human description, empty when unknown.
        setup_language: Language family driving `womm setup` ("python" or
            "javascript"), empty when the manifest declares none.
        copied_from: Directory a user template was copied from, ``None`` for
            official templates and for entries registered by path.
        storage: Stable directory of WOMM's copy, holding every version;
            ``None`` when WOMM keeps no copy.
        store_version: Version of the copy ``source`` renders from; 0 for a
            copy made before versioning.
        store_versions: Number of versions kept in ``storage``.
    """

    id: str
    origin: TemplateOrigin
    source: Path
    version: str = ""
    description: str = ""
    setup_language: str = ""
    copied_from: Path | None = None
    storage: Path | None = None
    store_version: int = 0
    store_versions: int = 0

    @property
    def qualified_id(self) -> str:
        """Get the fully-qualified, unambiguous identifier."""
        return f"{self.origin.value}/{self.id}"


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["TemplateEntry", "TemplateOrigin"]
