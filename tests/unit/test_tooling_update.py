"""Safety boundaries of staged, opt-in tooling migrations."""

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from womm.commands.project.setup import setup_group
from womm.exceptions.project import ProjectServiceError
from womm.services.project.config_document import ConfigDocument
from womm.services.project.tooling_environment import ToolingEnvironment, execute
from womm.services.project.tooling_migrations import apply_moves, check_transition
from womm.services.project.tooling_update_service import (
    ToolingUpdateService,
    confined,
    declarations,
)
from womm.shared.paths import packaged_assets


@pytest.fixture
def registry():
    return json.loads(
        packaged_assets().joinpath("migrations", "tooling.json").read_text("utf-8")
    )


@pytest.mark.parametrize(
    "suffix,text",
    [
        (".toml", '# keep\r\nold = true # local\r\n[user]\r\nvalue = "custom"\r\n'),
        (
            ".jsonc",
            '{/* keep */\r\n"old": true, // local\r\n"user": {"value": "custom"},\r\n}\r\n',
        ),
    ],
)
def test_roundtrip_move_preserves_values_and_comments(tmp_path, suffix, text):
    path = tmp_path / ("config" + suffix)
    path.write_bytes(text.encode())
    document = ConfigDocument(path)
    assert document.content() == text.encode()
    document.move(["old"], ["lint", "new"])
    document.write()
    edited = ConfigDocument(path)
    assert not edited.has(["old"])
    assert edited.get(["lint", "new"]) is True
    assert edited.get(["user", "value"]) == "custom"
    assert b"keep" in path.read_bytes()
    assert b"local" in path.read_bytes()
    assert b"\r\n" in path.read_bytes()


@pytest.mark.parametrize("value", ['["E"]', '{a = "b"}'])
def test_block_requires_permission_and_conflicts_never_force(tmp_path, value):
    path = tmp_path / "ruff.toml"
    path.write_text(f"old = {value}\n", encoding="utf-8")
    rule = {
        "id": "test",
        "operation": "move",
        "keys": ["old"],
        "source_prefix": [],
        "destination_prefix": ["lint"],
    }
    document = ConfigDocument(path)
    with pytest.raises(ProjectServiceError, match="allow-destructive-actions"):
        apply_moves(document, [], rule, False)
    assert apply_moves(document, [], rule, True)
    assert not apply_moves(document, [], rule, True)
    document.set(["old"], "conflicting")
    with pytest.raises(ProjectServiceError, match="Conflicting"):
        apply_moves(document, [], rule, True)


def test_unknown_version_boundary_cannot_be_forced(registry):
    assert not check_transition(registry, "ruff", "0.17.2", "0.17.9", False)
    with pytest.raises(ProjectServiceError, match="no reviewed migration"):
        check_transition(registry, "ruff", "0.16.0", "0.17.2", True)
    with pytest.raises(ProjectServiceError, match="allow-destructive-actions"):
        check_transition(registry, "@biomejs/biome", "1.9.4", "2.6.8", False)
    assert check_transition(registry, "@biomejs/biome", "1.9.4", "2.6.8", True)


@pytest.fixture
def project(tmp_path, monkeypatch):
    out = tmp_path / "project"
    out.mkdir()
    (out / ".womm-template.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "template": "official/python",
                "choices": {"type_checker": "ty"},
            }
        ),
        encoding="utf-8",
    )
    (out / "pyproject.toml").write_text(
        '# custom\n[project]\nname = "acme"\nversion = "1.0"\n[dependency-groups]\ndev = ["ruff~=0.17.2", "custom-tool>=1"] # keep\n[tool.ruff]\ndummy-variable-rgx = "_.*" # local\n',
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setattr(
        ToolingEnvironment,
        "versions",
        lambda _self, _path, names: dict.fromkeys(names, "0.17.2"),
    )
    monkeypatch.setattr(
        ToolingEnvironment,
        "resolve",
        lambda _self, _path, names: dict.fromkeys(names, "0.17.3"),
    )
    monkeypatch.setattr(
        ToolingEnvironment, "validate", lambda *_args: calls.append("validate")
    )
    monkeypatch.setattr(
        ToolingEnvironment, "synchronize", lambda *_args: calls.append("synchronize")
    )
    return out, calls


def snapshot(project):
    return {p.name: p.read_bytes() for p in project.iterdir() if p.is_file()}


def test_dry_run_and_declined_confirmation_never_write(project):
    out, calls = project
    before = snapshot(out)
    result = ToolingUpdateService().update(out, dry_run=True)
    assert (
        result.dry_run
        and result.migrations
        and result.files == [".womm-update.json", "pyproject.toml"]
    )
    assert "ty" not in {row[0] for row in result.updates}
    assert snapshot(out) == before
    ToolingUpdateService().update(out, approve=lambda _report: False)
    assert snapshot(out) == before
    assert "synchronize" not in calls


def test_apply_backs_up_and_keeps_generation_provenance(project):
    out, calls = project
    before = snapshot(out)
    result = ToolingUpdateService().update(out)
    assert result.success and calls == ["validate", "synchronize"]
    assert (result.backup_path / "pyproject.toml").read_bytes() == before[
        "pyproject.toml"
    ]
    assert (out / ".womm-template.json").read_bytes() == before[".womm-template.json"]
    data = tomllib.loads((out / "pyproject.toml").read_text("utf-8"))
    assert data["tool"]["ruff"]["lint"]["dummy-variable-rgx"] == "_.*"
    assert data["dependency-groups"]["dev"] == ["ruff~=0.17.2", "custom-tool>=1"]
    assert (
        len(json.loads((out / ".womm-update.json").read_text("utf-8"))["updates"]) == 1
    )
    assert not (out / ".womm-update.lock").exists()


def test_failed_install_restores_every_file(project, monkeypatch):
    out, _ = project
    before = snapshot(out)

    def fail(*_args):
        raise OSError("simulated install failure")

    monkeypatch.setattr(ToolingEnvironment, "synchronize", fail)
    with pytest.raises(ProjectServiceError, match="original files restored"):
        ToolingUpdateService().update(out)
    assert snapshot(out) == before
    assert list((out / ".womm-backups/update").iterdir())


def test_concurrent_edit_is_not_overwritten(project):
    out, calls = project

    def approve(_report):
        (out / "pyproject.toml").write_text("# editor changed this\n", encoding="utf-8")
        return True

    with pytest.raises(ProjectServiceError, match="changed while"):
        ToolingUpdateService().update(out, approve=approve)
    assert (out / "pyproject.toml").read_text("utf-8") == "# editor changed this\n"
    assert "synchronize" not in calls


def test_required_block_permission_blocks_entire_profile(project):
    out, calls = project
    path = out / "pyproject.toml"
    path.write_text(path.read_text("utf-8") + 'select = ["E"]\n', encoding="utf-8")
    before = snapshot(out)
    with pytest.raises(ProjectServiceError, match="allow-destructive-actions"):
        ToolingUpdateService().update(out)
    assert snapshot(out) == before and "synchronize" not in calls
    assert ToolingUpdateService().update(out, allow_destructive_actions=True).success


def test_dev_groups_and_duplicate_json_keys(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        '[dependency-groups]\ndev = [{include-group="lint"}]\nlint = ["ruff~=0.17.2"]\n',
        encoding="utf-8",
    )
    assert declarations(ConfigDocument(path), "python")[0][2] == "ruff"
    path = tmp_path / "biome.jsonc"
    path.write_text('{"key":1, "key":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        ConfigDocument(path)


@pytest.mark.parametrize(
    "args",
    [["--dry-run"], ["--update", "python"], ["--allow-destructive-actions", "detect"]],
)
def test_cli_rejects_misplaced_update_flags(args):
    result = CliRunner().invoke(setup_group, args)
    assert result.exit_code == 2


def test_missing_source_version_and_target_failure_leave_original_untouched(
    project, monkeypatch
):
    out, calls = project
    before = snapshot(out)
    monkeypatch.setattr(
        ToolingEnvironment,
        "versions",
        lambda _self, _path, names: dict.fromkeys(names, ""),
    )
    with pytest.raises(ProjectServiceError, match="no project-local"):
        ToolingUpdateService().update(out)
    assert snapshot(out) == before and not calls


def test_target_validation_failure_never_installs(project, monkeypatch):
    out, calls = project
    before = snapshot(out)

    def fail(*_args):
        raise ProjectServiceError("validation", "invalid target configuration")

    monkeypatch.setattr(ToolingEnvironment, "validate", fail)
    with pytest.raises(ProjectServiceError, match="invalid target"):
        ToolingUpdateService().update(out)
    assert snapshot(out) == before and not calls


def test_existing_update_lock_blocks_apply(project):
    out, calls = project
    (out / ".womm-update.lock").write_text("another update", encoding="utf-8")
    before = snapshot(out)
    with pytest.raises(ProjectServiceError, match="Another update"):
        ToolingUpdateService().update(out)
    assert snapshot(out) == before and "synchronize" not in calls


def test_update_paths_cannot_escape_or_follow_links(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    with pytest.raises(ProjectServiceError, match="leaves the project"):
        confined(root, "../outside.toml")
    linked = root / "pyproject.toml"
    original = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == linked or original(path)
    )
    with pytest.raises(ProjectServiceError, match="Linked update path"):
        confined(root, "pyproject.toml")


def test_installed_version_must_agree_with_native_lock(tmp_path, monkeypatch):
    from womm.services.project import tooling_environment

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="acme"\nversion="1"\n', encoding="utf-8"
    )
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname="ruff"\nversion="0.17.3"\n', encoding="utf-8"
    )
    (tmp_path / ".venv").mkdir()
    monkeypatch.setattr(
        tooling_environment, "execute", lambda *_args: '{"ruff":"0.17.2"}'
    )
    monkeypatch.setattr(
        ToolingEnvironment, "python", staticmethod(lambda _project: Path("python"))
    )
    with pytest.raises(ProjectServiceError, match="differs from the lockfile"):
        ToolingEnvironment(tmp_path, "python").versions(tmp_path, ["ruff"])


def test_staging_can_update_yarn_locks_without_weakening_final_ci_install(
    tmp_path, monkeypatch
):
    from womm.services.project import tooling_environment

    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("YARN_ENABLE_IMMUTABLE_INSTALLS", "true")
    monkeypatch.setenv("YARN_ENABLE_HARDENED_MODE", "true")
    environments = []

    def run(command, **kwargs):
        environments.append(kwargs["env"])
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(tooling_environment.subprocess, "run", run)
    execute(["yarn", "install"], tmp_path, staging=True)
    execute(["yarn", "install", "--immutable"], tmp_path)
    assert environments[0]["YARN_ENABLE_IMMUTABLE_INSTALLS"] == "false"
    assert environments[1]["YARN_ENABLE_IMMUTABLE_INSTALLS"] == "true"
    assert all(
        env["CI"] == "true" and env["YARN_ENABLE_HARDENED_MODE"] == "true"
        for env in environments
    )


def test_pip_update_keeps_declared_extras(tmp_path, monkeypatch):
    from womm.services.project import tooling_environment

    (tmp_path / "pyproject.toml").write_text(
        '[dependency-groups]\ndev=[{include-group="tests"}]\ntests=["pytest[testing]~=9.1.1"]\n',
        encoding="utf-8",
    )
    commands = []

    def execute_fake(command, _project):
        commands.append(command)
        return "pytest==9.1.2\n"

    monkeypatch.setattr(tooling_environment, "execute", execute_fake)
    monkeypatch.setattr(
        ToolingEnvironment, "python", staticmethod(lambda _project: Path("python"))
    )
    monkeypatch.setattr(
        ToolingEnvironment, "versions", lambda *_args: {"pytest": "9.1.2"}
    )
    ToolingEnvironment(tmp_path, "python").synchronize(tmp_path, tmp_path, ["pytest"])
    assert "pytest[testing]==9.1.2" in commands[-1]


def test_cli_preview_and_confirmation_render_without_installing(project):
    out, calls = project
    before = snapshot(out)
    preview = CliRunner().invoke(
        setup_group, ["--update", "--path", str(out), "--dry-run"]
    )
    assert preview.exit_code == 0, preview.output
    assert "ruff" in preview.output and "Target" in preview.output
    cancelled = CliRunner().invoke(
        setup_group, ["--update", "--path", str(out)], input="n\n"
    )
    assert cancelled.exit_code == 0, cancelled.output
    assert "cancelled" in cancelled.output
    assert snapshot(out) == before and "synchronize" not in calls


@pytest.mark.slow
def test_real_pip_update_uses_only_project_local_tools(tmp_path):
    project = tmp_path / "pip-project"
    project.mkdir()
    (project / ".womm-template.json").write_text(
        json.dumps({"schema_version": 1, "template": "official/python"}),
        encoding="utf-8",
    )
    (project / "pyproject.toml").write_text(
        '[project]\nname="acme"\nversion="1.0"\n[dependency-groups]\ndev=["ruff==0.17.2"]\n',
        encoding="utf-8",
    )
    execute([sys.executable, "-m", "venv", str(project / ".venv")], project)
    python = str(ToolingEnvironment.python(project))
    execute([python, "-m", "pip", "install", "ruff==0.17.2"], project)
    result = ToolingUpdateService().update(project, approve=lambda _result: True)
    assert result.success and result.backup_path
    assert "ruff~=" in (project / "pyproject.toml").read_text("utf-8")
    assert not (project / "uv.lock").exists()


@pytest.mark.slow
def test_real_biome_legacy_transition_requires_consent(tmp_path):
    project = tmp_path / "biome-legacy"
    project.mkdir()
    (project / ".womm-template.json").write_text(
        json.dumps({"schema_version": 1, "template": "official/javascript"}),
        encoding="utf-8",
    )
    (project / "package.json").write_text(
        json.dumps(
            {
                "name": "acme",
                "private": True,
                "devDependencies": {"@biomejs/biome": "1.9.4"},
            }
        ),
        encoding="utf-8",
    )
    (project / "biome.json").write_text(
        json.dumps(
            {
                "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
                "organizeImports": {"enabled": True},
            }
        ),
        encoding="utf-8",
    )
    environment = ToolingEnvironment(project, "javascript")
    execute(
        [*environment.prefix(), "install", "--package-lock-only", "--ignore-scripts"],
        project,
    )
    before = snapshot(project)
    with pytest.raises(ProjectServiceError, match="allow-destructive-actions"):
        ToolingUpdateService().update(project)
    assert snapshot(project) == before
    result = ToolingUpdateService().update(
        project, allow_destructive_actions=True, approve=lambda _result: True
    )
    assert result.success and "biome-v1-to-v2" in result.migrations
    assert not ConfigDocument(project / "biome.json").has(["organizeImports"])


@pytest.mark.slow
@pytest.mark.parametrize(
    "language,answers",
    [
        ("python", {"tooling": "ruff", "type_checker": "ty"}),
        ("python", {"tooling": "black-isort", "type_checker": "mypy"}),
        ("python", {"tooling": "ruff", "type_checker": "pyright"}),
        ("javascript", {"tooling": "biome", "typescript": True}),
        (
            "javascript",
            {"tooling": "eslint-prettier", "framework": "vue", "typescript": True},
        ),
    ],
)
def test_generated_profiles_validate_with_real_target_tools(
    tmp_path, language, answers
):
    from womm.services.project.copier_project_creation_service import (
        CopierProjectCreationService,
        ProjectCreationRequest,
    )
    from womm.services.project.template_store_service import TemplateStoreService

    project = tmp_path / "generated"
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=TemplateStoreService()
            .resolve(f"official/{language}")
            .source,
            destination=project,
            answers={"project_name": "acme", "package_manager": "npm", **answers},
            defaults=True,
        )
    )
    environment = ToolingEnvironment(project, language)
    if language == "python":
        execute([*environment.prefix(), "lock"], project)
    else:
        execute(
            [
                *environment.prefix(),
                "install",
                "--package-lock-only",
                "--ignore-scripts",
            ],
            project,
        )
    before = snapshot(project)
    assert ToolingUpdateService().update(project, dry_run=True).success
    assert snapshot(project) == before


@pytest.mark.slow
@pytest.mark.parametrize(
    "language,package_manager",
    [
        ("python", "uv"),
        ("javascript", "npm"),
        ("javascript", "pnpm"),
        ("javascript", "yarn"),
        ("javascript", "bun"),
    ],
)
def test_real_native_resolver_validates_and_applies_update(
    tmp_path, language, package_manager
):
    project = tmp_path / "real"
    project.mkdir()
    (project / ".womm-template.json").write_text(
        json.dumps({"schema_version": 1, "template": f"official/{language}"}),
        encoding="utf-8",
    )
    if language == "python":
        manager = shutil.which("uv")
        if not manager:
            pytest.skip("uv unavailable")
        (project / "pyproject.toml").write_text(
            '[project]\nname="acme"\nversion="1.0"\nrequires-python=">=3.11"\n[dependency-groups]\ndev=["ruff==0.17.2"]\n[tool.uv]\npackage=false\n[tool.ruff]\ndummy-variable-rgx="_.*" # custom\n',
            encoding="utf-8",
        )
        execute([manager, "lock"], project)
    else:
        prefix = (
            [shutil.which("corepack"), "yarn"]
            if package_manager == "yarn"
            else [shutil.which(package_manager)]
        )
        if not prefix[0]:
            pytest.skip(f"{package_manager} unavailable")
        if package_manager == "yarn":
            # Match the official template instead of Corepack's global default.
            version = "4.6.0"
        else:
            version = execute([*prefix, "--version"], project).strip()
        (project / "package.json").write_text(
            json.dumps(
                {
                    "name": "acme",
                    "version": "1.0.0",
                    "private": True,
                    "packageManager": f"{package_manager}@{version}",
                    "devDependencies": {"@biomejs/biome": "2.6.8"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (project / "biome.jsonc").write_text(
            '{/* custom */"formatter":{"indentStyle":"space"}}'
            if package_manager == "yarn"
            else '{/* custom */"$schema":"./node_modules/@biomejs/biome/configuration_schema.json","formatter":{"indentStyle":"space"}}',
            encoding="utf-8",
        )
        args = (
            ["install", "--package-lock-only", "--ignore-scripts"]
            if package_manager == "npm"
            else ["install"]
            if package_manager == "yarn"
            else ["install", "--ignore-scripts"]
        )
        execute([*prefix, *args], project, staging=True)
    before = snapshot(project)
    preview = ToolingUpdateService().update(project, dry_run=True)
    assert preview.success and preview.files
    assert snapshot(project) == before
    applied = ToolingUpdateService().update(project, approve=lambda _result: True)
    assert applied.success and applied.backup_path
    again = ToolingUpdateService().update(project)
    assert again.message == "Tooling is already up to date"
