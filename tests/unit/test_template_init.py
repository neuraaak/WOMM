"""Tests for the template scaffolding command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from womm.commands.project.template import template_group
from womm.interfaces.project.template_store_interface import (
    TemplateStoreInterface,
)
from womm.services.project.template_store_service import TemplateStoreService


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOMM_HOME", str(tmp_path / "home"))


def test_init_creates_a_template_skeleton(tmp_path: Path):
    destination = tmp_path / "my-template"

    result = TemplateStoreInterface().init_template(
        destination,
        answers={"template_name": "my-template"},
        force=False,
        defaults=True,
    )

    assert result.success is True
    assert (destination / "copier.yml").is_file()
    assert (destination / "template").is_dir()
    assert (destination / "README.md").is_file()


def test_generated_skeleton_is_a_valid_template(tmp_path: Path):
    destination = tmp_path / "my-template"
    TemplateStoreInterface().init_template(
        destination,
        answers={"template_name": "my-template"},
        force=False,
        defaults=True,
    )

    entry = TemplateStoreService().add("mine", destination)

    assert entry.qualified_id == "user/mine"


def test_init_refuses_a_non_empty_destination(tmp_path: Path):
    destination = tmp_path / "busy"
    destination.mkdir()
    (destination / "x.txt").write_text("x", encoding="utf-8")

    result = TemplateStoreInterface().init_template(
        destination, answers={}, force=False, defaults=True
    )

    assert result.success is False
    assert "--force" in result.error


def test_init_command_scaffolds(tmp_path: Path):
    destination = tmp_path / "cli-template"

    result = CliRunner().invoke(
        template_group, ["init", str(destination), "--defaults"]
    )

    assert result.exit_code == 0
    assert (destination / "copier.yml").is_file()


def test_skeleton_carries_catalog_metadata_and_renders_a_readme(tmp_path: Path):
    from womm.services.project.copier_project_creation_service import (
        CopierProjectCreationService,
        ProjectCreationRequest,
    )

    destination = tmp_path / "my-template"
    TemplateStoreInterface().init_template(
        destination,
        answers={"template_description": 'My "quoted" template'},
        force=False,
        defaults=True,
    )
    entry = TemplateStoreService().add("mine", destination)
    project = tmp_path / "project"
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=entry.source,
            destination=project,
            answers={"project_name": "acme"},
            defaults=True,
        )
    )

    assert entry.description == 'My "quoted" template'
    assert entry.version == "0.1.0"
    assert (project / "README.md").read_text(encoding="utf-8").startswith("# acme")
    assert not (project / ".gitkeep").exists()


@pytest.mark.parametrize("name", ["official/x", "user/x", "a/b/c", "ns/.x", "a\\b"])
def test_init_refuses_names_that_template_add_refuses(tmp_path: Path, name: str):
    result = TemplateStoreInterface().init_template(
        tmp_path / "t", answers={"template_name": name}, defaults=True
    )

    assert result.success is False
    assert "template_name" in result.error


def test_init_readme_uses_a_namespaced_identifier(tmp_path: Path):
    destination = tmp_path / "t"
    TemplateStoreInterface().init_template(
        destination, answers={"template_name": "neuraaak/my-tpl"}, defaults=True
    )

    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert "womm template add neuraaak/my-tpl" in readme
    assert "womm create user/neuraaak/my-tpl" in readme
