"""Tests for the copies WOMM keeps of user templates."""

import json
import shutil
from pathlib import Path

import pytest

from womm.exceptions.project import ProjectServiceError
from womm.interfaces.project.template_store_interface import TemplateStoreInterface
from womm.services.project.copier_project_creation_service import (
    CopierProjectCreationService,
    ProjectCreationRequest,
)
from womm.services.project.template_store_service import TemplateStoreService


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    monkeypatch.setenv("WOMM_HOME", str(home))
    return home


@pytest.fixture
def original(tmp_path: Path) -> Path:
    """A template directory, with a .git folder that must not be copied."""
    root = tmp_path / "original"
    (root / "template").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / "copier.yml").write_text(
        "_subdirectory: template\nproject_name:\n  type: str\n  default: demo\n",
        encoding="utf-8",
    )
    (root / "template" / "README.md.jinja").write_text(
        "# {{ project_name }}\n", encoding="utf-8"
    )
    return root


def _render(entry_source: Path, destination: Path) -> str:
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=entry_source,
            destination=destination,
            answers={"project_name": "acme"},
            defaults=True,
        )
    )
    return (destination / "README.md").read_text(encoding="utf-8")


def test_template_keeps_working_after_its_original_is_gone(
    original: Path, tmp_path: Path, isolated_home: Path
):
    TemplateStoreService().add("neuraaak/mine", original)
    shutil.rmtree(original)

    entry = TemplateStoreService().resolve("user/neuraaak/mine")

    assert entry.source == isolated_home / "templates" / "copies" / "neuraaak" / "mine"
    assert _render(entry.source, tmp_path / "out") == "# acme\n"


def test_copy_leaves_git_history_out(original: Path):
    entry = TemplateStoreService().add("mine", original)

    assert not (entry.source / ".git").exists()
    assert (entry.source / "template" / "README.md.jinja").is_file()


def test_update_without_source_fails_clearly_when_the_origin_is_gone(original: Path):
    store = TemplateStoreService()
    store.add("mine", original)
    shutil.rmtree(original)

    with pytest.raises(ProjectServiceError, match="origin is gone"):
        store.update("mine")
    assert store.resolve("mine").source.is_dir()


def test_update_replaces_the_copy_with_the_new_content(original: Path, tmp_path: Path):
    store = TemplateStoreService()
    store.add("mine", original)
    (original / "template" / "README.md.jinja").write_text(
        "# v2 {{ project_name }}\n", encoding="utf-8"
    )

    entry = store.update("mine")

    assert _render(entry.source, tmp_path / "out") == "# v2 acme\n"
    assert [p.name for p in entry.source.parent.iterdir()] == ["mine"]


def test_remove_deletes_the_copy_and_keeps_the_original(original: Path):
    store = TemplateStoreService()
    copy = store.add("mine", original).source

    store.remove("mine")

    assert not copy.exists()
    assert (original / "copier.yml").is_file()


def test_entry_registered_by_path_keeps_working_and_converts_on_update(
    original: Path, isolated_home: Path
):
    catalog = isolated_home / "templates" / "catalog.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        json.dumps({"templates": [{"id": "legacy", "source": str(original)}]}),
        encoding="utf-8",
    )
    store = TemplateStoreService()

    assert store.resolve("legacy").source == original.resolve()
    converted = store.update("legacy")

    assert converted.copied_from == original.resolve()
    assert converted.source.is_relative_to(isolated_home / "templates" / "copies")


def test_removing_an_entry_registered_by_path_never_deletes_its_directory(
    original: Path, isolated_home: Path
):
    catalog = isolated_home / "templates" / "catalog.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        json.dumps({"templates": [{"id": "legacy", "source": str(original)}]}),
        encoding="utf-8",
    )

    TemplateStoreService().remove("legacy")

    assert (original / "copier.yml").is_file()


@pytest.mark.parametrize("identifier", ["my:tpl", "tpl.", "-tpl", "con", "ns/aux.x"])
def test_identifiers_must_make_valid_directory_names(original: Path, identifier: str):
    with pytest.raises(ProjectServiceError, match="name or namespace/name"):
        TemplateStoreService().add(identifier, original)


@pytest.mark.parametrize("name", ["my:tpl", "con", "ns/aux.x"])
def test_init_refuses_names_that_are_not_valid_directory_names(
    tmp_path: Path, name: str
):
    result = TemplateStoreInterface().init_template(
        tmp_path / "t", answers={"template_name": name}, defaults=True
    )

    assert result.success is False
