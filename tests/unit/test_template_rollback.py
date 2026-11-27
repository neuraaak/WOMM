"""Tests for rolling back a stored template and rendering one of its versions."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from womm.commands.project.template import template_group
from womm.exceptions.project import ProjectServiceError
from womm.interfaces.project.create_interface import ProjectCreateInterface
from womm.services.project.template_store_service import TemplateStoreService


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOMM_HOME", str(tmp_path / "home"))


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "template").mkdir(parents=True)
    (root / "copier.yml").write_text(
        '_womm:\n  version: "1.0.0"\n_subdirectory: template\n', encoding="utf-8"
    )
    _content(root, "one")
    return root


def _content(root: Path, text: str) -> None:
    (root / "template" / "a.txt").write_text(f"{text}\n", encoding="utf-8")


@pytest.fixture
def three_versions(original: Path) -> TemplateStoreService:
    store = TemplateStoreService()
    store.add("mine", original)
    for text in ("two", "three"):
        _content(original, text)
        store.update("mine")
    return store


def _rendered(entry) -> str:
    return (entry.source / "template" / "a.txt").read_text()


def test_rollback_goes_to_the_previous_version(three_versions: TemplateStoreService):
    entry = three_versions.rollback("mine")

    assert entry.store_version == 2
    assert _rendered(three_versions.resolve("mine")) == "two\n"
    assert entry.store_versions == 3


def test_rollback_to_a_named_version_and_forward_again(
    three_versions: TemplateStoreService,
):
    assert three_versions.rollback("mine", "v1").store_version == 1
    assert three_versions.rollback("mine", "3").store_version == 3


def test_rollback_keeps_every_version(three_versions: TemplateStoreService):
    entry = three_versions.rollback("mine", "v1")

    assert sorted(p.name for p in entry.storage.iterdir() if p.is_dir()) == [
        "v1",
        "v2",
        "v3",
    ]


def test_an_update_after_a_rollback_reuses_the_matching_version(
    three_versions: TemplateStoreService,
):
    three_versions.rollback("mine", "v1")

    entry = three_versions.update("mine")  # the origin still holds "three"

    assert entry.store_version == 3
    assert entry.store_versions == 3


def test_an_unknown_version_is_refused(three_versions: TemplateStoreService):
    with pytest.raises(ProjectServiceError, match="Versions kept: v1, v2, v3"):
        three_versions.rollback("mine", "v9")


def test_the_oldest_version_has_nothing_before_it(
    three_versions: TemplateStoreService,
):
    three_versions.rollback("mine", "v1")

    with pytest.raises(ProjectServiceError, match="oldest version"):
        three_versions.rollback("mine")


@pytest.mark.parametrize("version", ["latest", "v0", "-1", ""])
def test_a_malformed_version_is_refused(
    three_versions: TemplateStoreService, version: str
):
    with pytest.raises(ProjectServiceError, match="Not a version"):
        three_versions.rollback("mine", version)


def test_a_single_copy_cannot_be_rolled_back(original: Path):
    store = TemplateStoreService()
    store.add("mine", original)

    with pytest.raises(ProjectServiceError, match="oldest version"):
        store.rollback("mine")


def test_official_templates_have_no_versions():
    with pytest.raises(ProjectServiceError, match="Only user templates"):
        TemplateStoreService().rollback("official/python")


def test_resolve_version_renders_a_kept_version_without_changing_the_current(
    three_versions: TemplateStoreService,
):
    entry = three_versions.resolve_version("mine@v1")

    assert _rendered(entry) == "one\n"
    assert entry.store_version == 1
    assert three_versions.resolve("mine").store_version == 3
    assert three_versions.resolve_version("user/mine@2").store_version == 2


def test_resolve_version_refuses_official_templates():
    with pytest.raises(ProjectServiceError, match="Only user templates"):
        TemplateStoreService().resolve_version("official/python@v1")


@pytest.mark.usefixtures("three_versions")
def test_create_from_a_kept_version(tmp_path: Path):
    result = ProjectCreateInterface().create_project(
        "mine@v1", tmp_path / "out", answers={}, defaults=True
    )

    assert result.success, result.error
    assert (tmp_path / "out" / "a.txt").read_text() == "one\n"
    assert "mine@v1" in result.message


@pytest.mark.usefixtures("three_versions")
def test_cli_rollback_and_show_history():
    result = CliRunner().invoke(template_group, ["rollback", "mine", "v2"])
    shown = CliRunner().invoke(template_group, ["show", "mine", "-v"])

    assert result.exit_code == 0, result.output
    assert "now renders from v2" in result.output
    assert "Stored version: v2 (3 kept)" in shown.output
    assert "* v2" in shown.output


def test_manifest_records_the_selected_version(three_versions: TemplateStoreService):
    entry = three_versions.rollback("mine", "v1")

    manifest = json.loads((entry.storage / "manifest.json").read_text("utf-8"))
    assert manifest["current"] == 1
