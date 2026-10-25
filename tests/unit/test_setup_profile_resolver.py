"""Tests for the setup profile resolver."""

from __future__ import annotations

from pathlib import Path

from womm.services.project.setup_profile_resolver import (
    SetupProfile,
    list_setup_identifiers,
    resolve_setup_profile,
)
from womm.services.project.template_store_service import TemplateStoreService
from womm.shared.models.template_source import TemplateEntry, TemplateOrigin


class FakeStore:
    """Minimal stand-in exposing only what the resolver needs."""

    def __init__(self, entries: list[TemplateEntry]) -> None:
        self._entries = entries

    def list_templates(self) -> list[TemplateEntry]:
        return self._entries


def _entry(id_: str, language: str) -> TemplateEntry:
    return TemplateEntry(
        id=id_,
        origin=TemplateOrigin.OFFICIAL,
        source=Path("/dev/null"),
        description=f"{id_} template",
        setup_language=language,
    )


def test_resolve_setup_profile_hits_catalog_entry():
    store = FakeStore([_entry("python", "python")])

    profile = resolve_setup_profile("python", store=store)

    assert profile == SetupProfile(
        language="python",
        template_source=Path("/dev/null"),
        answers={
            "project_name": "womm-setup",
            "description": "Project configured by WOMM",
            "with_vscode": True,
        },
    )


def test_resolve_setup_profile_ignores_catalog_entry_without_setup_metadata():
    store = FakeStore([_entry("my-service", "")])

    profile = resolve_setup_profile("my-service", store=store)

    assert profile is None


def test_resolve_setup_profile_falls_back_to_legacy_alias():
    store = FakeStore([_entry("javascript", "javascript")])

    react = resolve_setup_profile("react", store=store)
    vue = resolve_setup_profile("vue", store=store)

    assert react is not None and react.answers["framework"] == "react"
    assert vue is not None and vue.answers["framework"] == "vue"
    assert react.template_source == Path("/dev/null")


def test_resolve_setup_profile_returns_none_for_unknown_identifier():
    store = FakeStore([])

    assert resolve_setup_profile("cobol", store=store) is None


def test_list_setup_identifiers_lists_catalog_then_aliases():
    store = FakeStore([_entry("python", "python"), _entry("my-service", "")])

    identifiers = list_setup_identifiers(store=store)

    ids = [identifier for identifier, _description in identifiers]
    assert ids == ["python", "react", "vue"]


def test_resolve_setup_profile_reads_the_real_official_catalog():
    profile = resolve_setup_profile("javascript", store=TemplateStoreService())

    assert profile is not None
    assert profile.language == "javascript"
    assert profile.template_source.is_dir()
