"""Tests for the versions WOMM keeps of each stored user template."""

import json
import shutil
from pathlib import Path

import pytest

from womm.exceptions.project import ProjectServiceError
from womm.services.project import template_store_versions as versions
from womm.services.project.template_store_service import TemplateStoreService


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    monkeypatch.setenv("WOMM_HOME", str(home))
    return home


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "template").mkdir(parents=True)
    (root / "copier.yml").write_text(
        '_womm:\n  version: "1.0.0"\n_subdirectory: template\n', encoding="utf-8"
    )
    (root / "template" / "a.txt").write_text("one\n", encoding="utf-8")
    return root


def _manifest(entry) -> dict:
    return json.loads((entry.storage / "manifest.json").read_text("utf-8"))


def test_each_change_is_kept_as_a_new_version(original: Path):
    store = TemplateStoreService()
    first = store.add("mine", original)
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")

    second = store.update("mine")

    assert first.source.name == "v1"
    assert second.source.name == "v2"
    assert (second.storage / "v1" / "template" / "a.txt").read_text() == "one\n"
    assert (second.source / "template" / "a.txt").read_text() == "two\n"
    assert _manifest(second)["current"] == 2
    assert [v["number"] for v in _manifest(second)["versions"]] == [1, 2]


def test_an_identical_copy_creates_no_version(original: Path):
    store = TemplateStoreService()
    store.add("mine", original)

    entry = store.update("mine")

    assert (entry.store_version, entry.store_versions) == (1, 1)
    assert not (entry.storage / "v2").exists()


def test_the_catalog_keeps_the_stable_directory(original: Path, isolated_home: Path):
    store = TemplateStoreService()
    store.add("mine", original)
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")
    store.update("mine")
    # Any later catalog write must not pin a version.
    store.add("other", original)

    catalog = json.loads((isolated_home / "templates" / "catalog.json").read_text())
    sources = {item["id"]: Path(item["source"]).name for item in catalog["templates"]}
    assert sources == {"mine": "mine", "other": "other"}
    assert store.resolve("mine").source.name == "v2"


def test_a_flat_copy_becomes_v1_before_the_new_version(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    root = entry.storage
    # Lay the copy out as WOMM 5.5 did: flat in the stable directory.
    shutil.rmtree(root)
    shutil.copytree(original, root)
    assert store.resolve("mine").source == root
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")

    updated = store.update("mine")

    assert sorted(p.name for p in root.iterdir()) == ["manifest.json", "v1", "v2"]
    assert (root / "v1" / "template" / "a.txt").read_text() == "one\n"
    assert updated.source == root / "v2"


def test_an_orphan_version_directory_is_never_reused(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    (entry.storage / "v2").mkdir()
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")

    updated = store.update("mine")

    assert updated.source.name == "v3"


def test_a_busy_template_is_refused(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    lock = entry.storage.with_name(".mine.lock")
    lock.mkdir()
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")

    with pytest.raises(ProjectServiceError, match="Another WOMM command"):
        store.update("mine")
    assert store.resolve("mine").source.name == "v1"


def test_an_invalid_manifest_is_an_error(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    (entry.storage / "manifest.json").write_text("{", encoding="utf-8")

    with pytest.raises(ProjectServiceError, match="manifest is invalid"):
        store.resolve("mine")


def test_remove_deletes_every_version_and_keeps_the_namespace(original: Path):
    store = TemplateStoreService()
    store.add("team/one", original)
    kept = store.add("team/two", original)
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")
    removed = store.update("team/one")

    store.remove("team/one")

    assert not removed.storage.exists()
    assert kept.storage.is_dir()


def test_an_update_from_the_store_itself_is_refused(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)

    with pytest.raises(ProjectServiceError, match="WOMM's own copy"):
        store.update("mine", entry.source)


def test_tree_hash_covers_names_not_only_contents(tmp_path: Path):
    one, two = tmp_path / "one", tmp_path / "two"
    for root, name in ((one, "a.txt"), (two, "b.txt")):
        root.mkdir()
        (root / name).write_text("same\n", encoding="utf-8")

    assert versions.tree_hash(one) != versions.tree_hash(two)


def test_an_interrupted_migration_keeps_the_flat_copy(
    original: Path, monkeypatch: pytest.MonkeyPatch
):
    store = TemplateStoreService()
    root = store.add("mine", original).storage
    shutil.rmtree(root)
    shutil.copytree(original, root)

    def broken(*_: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(versions, "_copy_tree", broken)
    with pytest.raises(ProjectServiceError, match="could not be versioned"):
        store.update("mine")

    assert store.resolve("mine").source == root
    assert (root / "template" / "a.txt").read_text() == "one\n"
    assert not (root / "manifest.json").exists()


def test_a_busy_template_is_neither_unregistered_nor_deleted(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    entry.storage.with_name(".mine.lock").mkdir()

    with pytest.raises(ProjectServiceError, match="Another WOMM command"):
        store.remove("mine")

    assert store.resolve("mine").source == entry.source
    assert (entry.source / "copier.yml").is_file()


def test_a_lock_never_clashes_with_a_template_identifier(original: Path):
    store = TemplateStoreService()
    store.add("legit.lock", original)

    assert store.add("legit", original).source.name == "v1"


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        "null",
        '"text"',
        '{"schema_version": 1, "current": 1, "versions": {}}',
        '{"schema_version": true, "current": 1, "versions": [{"number": 1}]}',
        '{"schema_version": 1, "current": true,'
        ' "versions": [{"number": 1, "tree_hash": "' + "a" * 64 + '"}]}',
        '{"schema_version": 1, "current": 1,'
        ' "versions": [{"number": 1, "tree_hash": "x"}]}',
    ],
)
def test_every_malformed_manifest_is_a_readable_error(original: Path, content: str):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    (entry.storage / "manifest.json").write_text(content, encoding="utf-8")

    with pytest.raises(ProjectServiceError, match="manifest is invalid"):
        store.resolve("mine")


def test_a_failed_migration_commit_leaves_no_v1_behind(
    original: Path, monkeypatch: pytest.MonkeyPatch
):
    store = TemplateStoreService()
    root = store.add("mine", original).storage
    shutil.rmtree(root)
    shutil.copytree(original, root)
    real_write = versions._write_manifest

    def broken(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(versions, "_write_manifest", broken)
    with pytest.raises(ProjectServiceError, match="could not be versioned"):
        store.update("mine")
    monkeypatch.setattr(versions, "_write_manifest", real_write)

    assert not (root / "v1").exists()
    (original / "template" / "a.txt").write_text("two\n", encoding="utf-8")
    assert store.update("mine").source == root / "v2"


def test_a_flat_copy_holding_a_version_name_is_refused(original: Path):
    store = TemplateStoreService()
    root = store.add("mine", original).storage
    shutil.rmtree(root)
    shutil.copytree(original, root)
    (root / "v1").mkdir()

    with pytest.raises(ProjectServiceError, match="Move it aside"):
        store.update("mine")
    assert store.resolve("mine").source == root


def test_a_damaged_current_version_is_replaced_not_kept(original: Path):
    store = TemplateStoreService()
    entry = store.add("mine", original)
    (entry.source / "copier.yml").unlink()

    repaired = store.update("mine")

    assert repaired.source.name == "v2"
    assert (repaired.source / "copier.yml").is_file()
    assert not (entry.source / "copier.yml").exists()


def test_each_version_records_the_template_version(original: Path):
    entry = TemplateStoreService().add("mine", original)

    assert _manifest(entry)["versions"][0]["template_version"] == "1.0.0"


def test_a_failed_catalog_write_keeps_the_removed_copy(
    original: Path, monkeypatch: pytest.MonkeyPatch
):
    store = TemplateStoreService()
    entry = store.add("mine", original)

    def broken(*_: object) -> None:
        raise ProjectServiceError(operation="save_catalog", reason="disk full")

    monkeypatch.setattr(store, "_save_user_entries", broken)
    with pytest.raises(ProjectServiceError, match="disk full"):
        store.remove("mine")

    assert (entry.source / "copier.yml").is_file()
    assert [p.name for p in entry.storage.parent.iterdir()] == ["mine"]
