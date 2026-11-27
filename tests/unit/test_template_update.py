"""Tests for ``womm template update`` on templates extracted from a project."""

import shutil
import subprocess
from pathlib import Path, PurePosixPath

import pytest
from click.testing import CliRunner

from womm.commands.project.template import template_group
from womm.exceptions.project import ProjectServiceError
from womm.interfaces.project.template_store_interface import (
    TemplateStoreInterface,
)
from womm.services.project.template_store_service import TemplateStoreService
from womm.services.project.template_update_service import TemplateUpdateService
from womm.shared.results.template_results import ChangeKind

GIT = shutil.which("git") or "git"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOMM_HOME", str(tmp_path / "home"))


def _git(root: Path, *args: str) -> None:
    subprocess.run([GIT, "-C", str(root), *args], check=True, capture_output=True)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "acme-app"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "core.autocrlf", "false")
    for name, text in {
        "pyproject.toml": '[project]\nname = "acme-app"\n',
        "src/acme_app/__init__.py": "",
        "config.txt": "plain v1\n",
        "notes.txt": "notes v1\n",
        "old.txt": "old\n",
    }.items():
        _write(root / name, text)
    _git(root, "add", "-A")
    return root


@pytest.fixture
def template(project: Path, tmp_path: Path) -> Path:
    destination = tmp_path / "tpl"
    result = TemplateStoreInterface().init_template(
        destination,
        answers={"template_name": "acme"},
        defaults=True,
        source=project,
    )
    assert result.success, result.error
    return destination


def _track(project: Path) -> None:
    _git(project, "add", "-A")


def _kinds(plan) -> dict[str, ChangeKind]:
    return {c.source.as_posix(): c.kind for c in plan.changes}


def _version(template: Path) -> str:
    import yaml

    return yaml.safe_load((template / "copier.yml").read_text("utf-8"))["_womm"][
        "version"
    ]


# ///////////////////////////////////////////////////////////////
# CLASSIFICATION
# ///////////////////////////////////////////////////////////////


def test_a_project_change_is_applied_and_bumps_the_version(
    project: Path, template: Path
):
    _write(project / "config.txt", "plain v2\n")
    service = TemplateUpdateService()

    plan = service.plan(template)
    outcome = service.apply(plan, {})

    assert _kinds(plan) == {"config.txt": ChangeKind.UPDATED}
    assert (template / "template" / "config.txt").read_text() == "plain v2\n"
    assert outcome.version == ("0.1.0", "0.1.1")
    assert _version(template) == "0.1.1"


def test_nothing_to_do_changes_nothing(template: Path):
    service = TemplateUpdateService()
    before = (template / "copier.yml").read_bytes()

    outcome = service.apply(service.plan(template), {})

    assert outcome.version is None
    assert (template / "copier.yml").read_bytes() == before


def test_an_author_edit_is_kept(template: Path):
    _write(template / "template" / "notes.txt", "my notes\n")

    plan = TemplateUpdateService().plan(template)

    assert plan.changes == []
    assert plan.kept == 1


def test_both_sides_changed_is_a_conflict(project: Path, template: Path):
    _write(template / "template" / "notes.txt", "my notes\n")
    _write(project / "notes.txt", "notes v2\n")
    service = TemplateUpdateService()

    plan = service.plan(template)
    assert _kinds(plan) == {"notes.txt": ChangeKind.CONFLICT}
    service.apply(plan, {PurePosixPath("notes.txt"): False})

    assert (template / "template" / "notes.txt").read_text() == "my notes\n"
    # Settled: the same conflict is not asked again.
    assert TemplateUpdateService().plan(template).changes == []


def test_a_conflict_left_pending_is_asked_again(project: Path, template: Path):
    _write(template / "template" / "notes.txt", "my notes\n")
    _write(project / "notes.txt", "notes v2\n")
    service = TemplateUpdateService()

    outcome = service.apply(service.plan(template), {})

    assert outcome.pending == ["notes.txt"]
    assert _kinds(service.plan(template)) == {"notes.txt": ChangeKind.CONFLICT}


def test_a_new_file_is_asked_then_added(project: Path, template: Path):
    _write(project / "extra.txt", "extra\n")
    _track(project)
    service = TemplateUpdateService()

    plan = service.plan(template)
    assert _kinds(plan) == {"extra.txt": ChangeKind.NEW}
    service.apply(plan, {})  # pending: not added, asked again
    assert not (template / "template" / "extra.txt").exists()
    plan = service.plan(template)
    service.apply(plan, {PurePosixPath("extra.txt"): True})

    assert (template / "template" / "extra.txt").read_text() == "extra\n"


def test_a_removed_file_left_pending_is_proposed_again(project: Path, template: Path):
    _git(project, "rm", "-q", "-f", "old.txt")
    service = TemplateUpdateService()

    service.apply(service.plan(template), {})
    assert (template / "template" / "old.txt").is_file()
    plan = service.plan(template)
    assert _kinds(plan) == {"old.txt": ChangeKind.REMOVABLE}
    service.apply(plan, {PurePosixPath("old.txt"): True})

    assert not (template / "template" / "old.txt").exists()
    assert TemplateUpdateService().plan(template).changes == []


def test_a_file_deleted_from_the_template_is_not_brought_back(
    project: Path, template: Path
):
    (template / "template" / "notes.txt").unlink()

    assert TemplateUpdateService().plan(template).changes == []
    _write(project / "notes.txt", "notes v2\n")
    assert _kinds(TemplateUpdateService().plan(template)) == {
        "notes.txt": ChangeKind.CONFLICT
    }


def test_a_file_that_starts_holding_the_name_is_renamed(project: Path, template: Path):
    _write(project / "config.txt", "for acme-app\n")
    service = TemplateUpdateService()

    plan = service.plan(template)
    service.apply(plan, {})

    assert _kinds(plan) == {"config.txt": ChangeKind.UPDATED}
    assert not (template / "template" / "config.txt").exists()
    assert (template / "template" / "config.txt.womm").read_text() == (
        "for [[@ project_slug @]]\n"
    )


def test_a_new_file_over_one_of_yours_is_a_conflict(project: Path, template: Path):
    _write(template / "template" / "extra.txt", "mine\n")
    _write(project / "extra.txt", "theirs\n")
    _track(project)

    plan = TemplateUpdateService().plan(template)

    assert _kinds(plan) == {"extra.txt": ChangeKind.CONFLICT}


# ///////////////////////////////////////////////////////////////
# SAFETY
# ///////////////////////////////////////////////////////////////


def test_a_template_changed_after_the_plan_is_refused(project: Path, template: Path):
    _write(project / "config.txt", "plain v2\n")
    service = TemplateUpdateService()
    plan = service.plan(template)
    _write(template / "template" / "config.txt", "edited meanwhile\n")

    with pytest.raises(ProjectServiceError, match="changed since"):
        service.apply(plan, {})
    assert (template / "template" / "config.txt").read_text() == "edited meanwhile\n"


def test_a_failed_write_restores_the_template(
    project: Path, template: Path, monkeypatch: pytest.MonkeyPatch
):
    _write(project / "config.txt", "plain v2\n")
    service = TemplateUpdateService()
    plan = service.plan(template)
    manifest = (template / "copier.yml").read_bytes()

    def broken(*_: object) -> None:
        raise OSError("disk full")

    import womm.services.project.template_update_service as module

    monkeypatch.setattr(module, "write_trace", broken)
    with pytest.raises(ProjectServiceError, match="restored"):
        service.apply(plan, {})

    assert (template / "template" / "config.txt").read_text() == "plain v1\n"
    assert (template / "copier.yml").read_bytes() == manifest


def test_an_identity_change_is_refused(project: Path, template: Path):
    _write(project / "pyproject.toml", '[project]\nname = "other"\n')

    with pytest.raises(ProjectServiceError, match="identity changed"):
        TemplateUpdateService().plan(template)


def test_a_changed_contract_is_refused(template: Path):
    manifest = template / "copier.yml"
    manifest.write_text(
        manifest.read_text("utf-8").replace('".womm"', '".tmpl"'), encoding="utf-8"
    )

    with pytest.raises(ProjectServiceError, match="no longer matches"):
        TemplateUpdateService().plan(template)


def test_a_template_without_trace_cannot_be_updated_from_a_project(
    project: Path, tmp_path: Path
):
    plain = tmp_path / "plain"
    TemplateStoreInterface().init_template(
        plain, answers={"template_name": "plain"}, defaults=True
    )

    with pytest.raises(ProjectServiceError, match="no extraction trace"):
        TemplateUpdateService().plan(plain, project)


def test_the_version_bump_keeps_comments_and_line_endings(
    project: Path, template: Path
):
    manifest = template / "copier.yml"
    text = manifest.read_text("utf-8").replace(
        'version: "0.1.0"', 'version: "0.1.0"  # bumped by WOMM'
    )
    manifest.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    _write(project / "config.txt", "plain v2\n")
    service = TemplateUpdateService()

    service.apply(service.plan(template), {})

    data = manifest.read_bytes()
    assert b'version: "0.1.1"  # bumped by WOMM\r\n' in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_a_version_womm_cannot_raise_is_refused_before_writing(
    project: Path, template: Path
):
    manifest = template / "copier.yml"
    manifest.write_text(
        manifest.read_text("utf-8").replace('version: "0.1.0"', 'version: "next"'),
        encoding="utf-8",
    )
    _write(project / "config.txt", "plain v2\n")
    service = TemplateUpdateService()

    with pytest.raises(ProjectServiceError, match="X.Y.Z"):
        service.apply(service.plan(template), {})
    assert (template / "template" / "config.txt").read_text() == "plain v1\n"


# ///////////////////////////////////////////////////////////////
# COMMAND AND STORE
# ///////////////////////////////////////////////////////////////


def test_update_by_path_refreshes_the_linked_store_entry(project: Path, template: Path):
    TemplateStoreService().add("acme", template)
    _write(project / "config.txt", "plain v2\n")

    result = CliRunner().invoke(template_group, ["update", str(template)])

    assert result.exit_code == 0, result.output
    entry = TemplateStoreService().resolve("acme")
    assert entry.store_version == 2
    assert (entry.source / "template" / "config.txt").read_text() == "plain v2\n"
    assert entry.version == "0.1.1"


def test_update_by_id_updates_the_template_then_the_store(
    project: Path, template: Path
):
    TemplateStoreService().add("acme", template)
    _write(project / "config.txt", "plain v2\n")

    result = CliRunner().invoke(template_group, ["update", "acme"])

    assert result.exit_code == 0, result.output
    assert (template / "template" / "config.txt").read_text() == "plain v2\n"
    assert TemplateStoreService().resolve("acme").store_version == 2


def test_an_unregistered_template_is_updated_but_never_registered(
    project: Path, template: Path
):
    _write(project / "config.txt", "plain v2\n")

    result = CliRunner().invoke(template_group, ["update", str(template)])

    assert result.exit_code == 0, result.output
    assert TemplateStoreService().list_templates() == [
        e
        for e in TemplateStoreService().list_templates()
        if e.origin.value == "official"
    ]


def test_interactive_update_asks_and_can_be_cancelled(project: Path, template: Path):
    _write(project / "extra.txt", "extra\n")
    _track(project)

    result = CliRunner().invoke(
        template_group, ["update", str(template), "-I"], input="y\nn\n"
    )

    assert result.exit_code == 0, result.output
    assert "Cancelled" in result.output
    assert not (template / "template" / "extra.txt").exists()


# ///////////////////////////////////////////////////////////////
# REVIEW SCENARIOS
# ///////////////////////////////////////////////////////////////


def test_a_stored_version_is_never_updated_in_place(project: Path, template: Path):
    entry = TemplateStoreService().add("acme", template)
    _write(project / "config.txt", "plain v2\n")
    store = TemplateStoreInterface()

    by_path = store.plan_update(str(entry.source), project=project)
    other = TemplateStoreService().add("other", template)
    by_source = store.plan_update("acme", other.source)

    assert by_path.success is False
    assert "cannot be updated in place" in by_path.error
    assert by_source.success is False
    assert (entry.source / "template" / "config.txt").read_text() == "plain v1\n"


@pytest.mark.parametrize(
    ("local", "first", "second"),
    [
        # The project starts naming itself in the file: config.txt -> .womm
        ("config.txt", "acme-app one\n", "acme-app two\n"),
        # The project stops naming itself in it: .womm -> config.txt
        ("named.txt.womm", "plain one\n", "plain two\n"),
    ],
)
def test_a_kept_file_across_a_rename_stays_tracked(
    project: Path, tmp_path: Path, local: str, first: str, second: str
):
    _write(project / "named.txt", "for acme-app\n")
    _track(project)
    destination = tmp_path / "tpl2"
    TemplateStoreInterface().init_template(
        destination, answers={"template_name": "acme"}, defaults=True, source=project
    )
    tpl = destination / "template"
    source = "config.txt" if local == "config.txt" else "named.txt"
    _write(tpl / local, "my edit\n")
    _write(project / source, first)
    service = TemplateUpdateService()

    plan = service.plan(destination)
    assert _kinds(plan) == {source: ChangeKind.CONFLICT}
    service.apply(plan, {PurePosixPath(source): False})
    assert TemplateUpdateService().plan(destination).changes == []
    _write(project / source, second)
    plan = service.plan(destination)
    assert _kinds(plan) == {source: ChangeKind.CONFLICT}
    service.apply(plan, {PurePosixPath(source): True})

    stem = source.split(".")[0]
    remaining = sorted(p.name for p in tpl.iterdir() if p.name.startswith(stem))
    assert len(remaining) == 1
    assert remaining[0] != local


def test_a_new_file_rendering_over_a_manual_one_is_a_conflict(
    project: Path, template: Path
):
    _write(template / "template" / "extra.txt", "mine\n")
    _write(project / "extra.txt", "for acme-app\n")
    _track(project)
    service = TemplateUpdateService()

    plan = service.plan(template)
    assert _kinds(plan) == {"extra.txt": ChangeKind.CONFLICT}
    service.apply(plan, {PurePosixPath("extra.txt"): True})

    assert not (template / "template" / "extra.txt").exists()
    assert (template / "template" / "extra.txt.womm").is_file()


def test_a_linked_manifest_is_refused(project: Path, template: Path, tmp_path: Path):
    outside = tmp_path / "outside.yml"
    outside.write_bytes((template / "copier.yml").read_bytes())
    (template / "copier.yml").unlink()
    try:
        (template / "copier.yml").symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links need a privilege on this machine")
    _write(project / "config.txt", "plain v2\n")

    with pytest.raises(ProjectServiceError, match="is a link"):
        TemplateUpdateService().plan(template)
    assert b'"0.1.0"' in outside.read_bytes()


def test_a_missing_required_question_is_refused(template: Path):
    import yaml

    manifest = template / "copier.yml"
    data = yaml.safe_load(manifest.read_text("utf-8"))
    del data["project_slug"]
    data["my_own_question"] = {"type": "str", "default": "x"}
    manifest.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ProjectServiceError, match="project_slug"):
        TemplateUpdateService().plan(template)


def test_a_failed_restore_keeps_the_backup(
    project: Path, template: Path, monkeypatch: pytest.MonkeyPatch
):
    import womm.services.project.template_update_service as module

    _write(project / "config.txt", "plain v2\n")
    service = TemplateUpdateService()
    plan = service.plan(template)
    real_copy = module.shutil.copy2
    calls = {"n": 0}

    def flaky_copy(src, dst, *args, **kwargs):
        calls["n"] += 1
        # Let the backup copies succeed, break every restore copy.
        if "womm-update-" in str(src):
            raise OSError("restore failed")
        return real_copy(src, dst, *args, **kwargs)

    def broken(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(module, "write_trace", broken)
    monkeypatch.setattr(module.shutil, "copy2", flaky_copy)
    with pytest.raises(ProjectServiceError, match="nor fully restored") as caught:
        service.apply(plan, {})

    backup = Path(str(caught.value).split("kept in ")[1].removesuffix("."))
    assert backup.is_dir()
    import json

    recovery = json.loads((backup / "recovery.json").read_text("utf-8"))
    saved = {Path(item["path"]).name: item["backup"] for item in recovery}
    assert (backup / saved["config.txt"]).read_text() == "plain v1\n"


@pytest.mark.skipif(__import__("os").name == "nt", reason="POSIX permissions")
def test_a_new_executable_keeps_its_mode(project: Path, template: Path):
    script = project / "run.sh"
    _write(script, "#!/bin/sh\n")
    script.chmod(0o755)
    _track(project)
    service = TemplateUpdateService()

    service.apply(service.plan(template), {PurePosixPath("run.sh"): True})

    assert (template / "template" / "run.sh").stat().st_mode & 0o111


def test_several_entries_from_one_template_update_it_in_place_only(
    project: Path, template: Path
):
    TemplateStoreService().add("one", template)
    TemplateStoreService().add("two", template)
    _write(project / "config.txt", "plain v2\n")

    preview = TemplateStoreInterface().plan_update(str(template))
    result = TemplateStoreInterface().apply_update(preview, {})

    assert preview.entry is None
    assert preview.other_ids == ["one", "two"]
    assert result.success and result.entry is None
    assert TemplateStoreService().resolve("one").store_version == 1


def test_keeping_both_files_of_one_path_leaves_a_readable_trace(tmp_path: Path):
    root = tmp_path / "acme"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "core.autocrlf", "false")
    _write(root / "pyproject.toml", '[project]\nname = "Acme.App"\n')
    _write(root / "Acme.App.txt", "old\n")
    _git(root, "add", "-A")
    template = tmp_path / "tpl"
    TemplateStoreInterface().init_template(
        template, answers={"template_name": "acme"}, defaults=True, source=root
    )
    _git(root, "rm", "-q", "-f", "Acme.App.txt")
    _write(root / "acme-app.txt", "new\n")
    _track(root)
    service = TemplateUpdateService()

    plan = service.plan(template)
    assert _kinds(plan) == {
        "Acme.App.txt": ChangeKind.REMOVABLE,
        "acme-app.txt": ChangeKind.CONFLICT,
    }
    service.apply(
        plan,
        {PurePosixPath("Acme.App.txt"): False, PurePosixPath("acme-app.txt"): False},
    )

    again = TemplateUpdateService().plan(template)
    assert set(_kinds(again)) == {"Acme.App.txt", "acme-app.txt"}
    kept = template / "template" / "[[@ project_name @]].txt"
    assert kept.read_text() == "old\n"


def test_questions_the_package_derives_from_are_required(tmp_path: Path):
    import yaml

    root = tmp_path / "foo"
    root.mkdir()
    _git(root, "init", "-q")
    _write(root / "pyproject.toml", '[project]\nname = "foo"\n')
    _write(root / "src/foo/__init__.py", "")
    _git(root, "add", "-A")
    template = tmp_path / "tpl"
    TemplateStoreInterface().init_template(
        template, answers={"template_name": "foo"}, defaults=True, source=root
    )
    manifest = template / "copier.yml"
    data = yaml.safe_load(manifest.read_text("utf-8"))
    del data["project_slug"]
    manifest.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ProjectServiceError, match="project_slug"):
        TemplateUpdateService().plan(template)


def test_from_without_a_known_template_directory_is_refused(
    project: Path, template: Path
):
    import json

    from womm.shared.paths import template_catalog_file

    TemplateStoreService().add("acme", template)
    catalog = template_catalog_file()
    payload = json.loads(catalog.read_text("utf-8"))
    payload["templates"][0]["copied_from"] = None
    catalog.write_text(json.dumps(payload), encoding="utf-8")

    preview = TemplateStoreInterface().plan_update("acme", project=project)

    assert preview.success is False
    assert "--from needs" in preview.error
