#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST PROJECT SETUP INTERFACE - Direct orchestration coverage
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""Direct tests for project setup orchestration."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import json
from pathlib import Path
from types import SimpleNamespace

# Third-party imports
import pytest

# Local imports
from womm.interfaces.project.setup_interface import ProjectSetupInterface
from womm.services.project.setup_profile_resolver import (
    SetupProfile,
    resolve_setup_profile,
)
from womm.shared.results import ProjectCreationResult, ProjectDetectionResult

# ///////////////////////////////////////////////////////////////
# PUBLIC SETUP WORKFLOWS
# ///////////////////////////////////////////////////////////////


def test_setup_project_reports_missing_directory_as_validation_failure(
    tmp_path: Path,
) -> None:
    result = ProjectSetupInterface().setup_project(
        tmp_path / "missing", project_type="python"
    )

    assert not result.success
    assert result.error.startswith("Failed to setup project:")
    assert "Project directory does not exist" in result.error


def test_setup_project_auto_detects_and_aggregates_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()
    monkeypatch.setattr(
        interface._detection_service,
        "detect_project_type",
        lambda _path: ProjectDetectionResult(success=True, project_type="python"),
    )
    monkeypatch.setattr(interface, "_check_dependencies", lambda _type: "")
    monkeypatch.setattr(
        interface, "_copy_vscode_config", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        interface,
        "_setup_python_project",
        lambda *_args, **_kwargs: {
            "files_modified": ["pyproject.toml"],
            "tools_configured": ["venv"],
            "warnings": ["partial warning"],
        },
    )

    result = interface.setup_project(tmp_path, setup_vscode=True)

    assert result.success
    assert result.project_type == "python"
    assert result.project_name == tmp_path.name
    assert result.files_modified == ["pyproject.toml"]
    assert result.tools_configured == ["vscode", "venv"]
    assert result.warnings == ["partial warning"]


def test_setup_project_returns_dependency_probe_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()
    monkeypatch.setattr(
        interface,
        "_check_dependencies",
        lambda _type: "Node.js runtime not found",
    )

    result = interface.setup_project(tmp_path, project_type="javascript")

    assert not result.success
    assert result.error == "Node.js runtime not found"


def test_setup_project_keeps_vscode_copy_failure_as_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()
    monkeypatch.setattr(interface, "_check_dependencies", lambda _type: "")

    def fail_copy(_path: Path, _type: str, **_kwargs: object) -> None:
        raise OSError("assets unavailable")

    monkeypatch.setattr(interface, "_copy_vscode_config", fail_copy)

    result = interface.setup_project(tmp_path, project_type="python", setup_vscode=True)

    assert result.success
    assert result.tools_configured is not None
    assert "vscode" not in result.tools_configured
    assert result.warnings == ["VSCode configuration skipped: assets unavailable"]


def test_setup_project_without_steps_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0"\n', encoding="utf-8"
    )
    interface = ProjectSetupInterface()

    result = interface.setup_project(tmp_path, project_type="python")

    assert result.success
    assert result.tools_configured == []
    assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml"]


def test_setup_project_rejects_unknown_type_via_resolver(tmp_path: Path) -> None:
    result = ProjectSetupInterface().setup_project(tmp_path, project_type="cobol")

    assert not result.success
    assert "Unsupported project type for setup: cobol" in result.error


def test_setup_project_resolves_a_catalog_identifier_beyond_the_legacy_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A future catalog entry (e.g. "django") must reach the python branch
    once it declares setup_language="python", without editing this file."""
    interface = ProjectSetupInterface()
    monkeypatch.setattr(
        "womm.interfaces.project.setup_interface.resolve_setup_profile",
        lambda _identifier: SetupProfile(
            language="python", template_source=tmp_path, answers={}
        ),
    )
    monkeypatch.setattr(interface, "_check_dependencies", lambda _profile: "")
    monkeypatch.setattr(
        interface, "_copy_vscode_config", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        interface,
        "_setup_python_project",
        lambda *_args, **_kwargs: {
            "files_modified": [],
            "tools_configured": ["venv"],
            "warnings": [],
        },
    )

    result = interface.setup_project(tmp_path, project_type="django")

    assert result.success
    assert result.project_type == "django"


# ///////////////////////////////////////////////////////////////
# PYTHON ORCHESTRATION
# ///////////////////////////////////////////////////////////////


@pytest.mark.parametrize(
    ("has_config", "expected_calls"),
    [(True, ["dependencies", "git", "git_hooks"]), (False, ["dependencies", "git"])],
)
def test_setup_python_installs_hooks_only_when_the_project_declares_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    has_config: bool,
    expected_calls: list[str],
) -> None:
    interface = ProjectSetupInterface()
    calls: list[str] = []
    if has_config:
        (tmp_path / ".pre-commit-config.yaml").touch()

    def succeed(name: str):
        def operation(_path: Path) -> ProjectCreationResult:
            calls.append(name)
            return ProjectCreationResult(success=True)

        return operation

    for method, name in [
        ("install_dev_dependencies", "dependencies"),
        ("setup_git_repository", "git"),
        ("install_git_hooks", "git_hooks"),
    ]:
        monkeypatch.setattr(interface._python_service, method, succeed(name))

    result = interface._setup_python_project(
        tmp_path,
        install_deps=True,
        setup_git_hooks=True,
    )

    assert calls == expected_calls
    assert result["tools_configured"] == expected_calls
    assert result["warnings"] == []


def test_setup_python_collects_failures_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()

    def fail_venv(_path: Path) -> ProjectCreationResult:
        raise OSError("venv unavailable")

    monkeypatch.setattr(
        interface._python_service, "setup_virtual_environment", fail_venv
    )
    monkeypatch.setattr(
        interface._python_service,
        "install_dev_dependencies",
        lambda _path: ProjectCreationResult(success=False),
    )
    monkeypatch.setattr(
        interface._python_service,
        "setup_git_repository",
        lambda _path: ProjectCreationResult(success=False),
    )
    monkeypatch.setattr(
        interface._python_service,
        "install_git_hooks",
        lambda _path: ProjectCreationResult(
            success=False, message="Git hooks not installed", error="no pre-commit"
        ),
    )
    (tmp_path / ".pre-commit-config.yaml").touch()

    result = interface._setup_python_project(
        tmp_path,
        virtual_env=True,
        install_deps=True,
        setup_git_hooks=True,
    )

    assert result["tools_configured"] == []
    assert result["warnings"] == [
        "Virtual environment setup skipped: venv unavailable",
        "Dependency installation failed",
        "Git repository setup failed",
        "Git hooks not installed: no pre-commit",
    ]


@pytest.mark.parametrize(
    ("install_deps", "expected_tools"),
    [(True, ["venv", "dependencies"]), (False, ["venv"])],
)
def test_setup_python_uses_uv_instead_of_pip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    install_deps: bool,
    expected_tools: list[str],
) -> None:
    interface = ProjectSetupInterface()
    uv_calls: list[bool] = []

    def uv_setup(_path: Path, deps: bool) -> ProjectCreationResult:
        uv_calls.append(deps)
        return ProjectCreationResult(success=True)

    def pip_step(_path: Path) -> ProjectCreationResult:
        raise AssertionError("pip must not run on a uv project")

    monkeypatch.setattr(interface._python_service, "setup_uv_environment", uv_setup)
    monkeypatch.setattr(
        interface._python_service, "setup_virtual_environment", pip_step
    )
    monkeypatch.setattr(interface._python_service, "install_dev_dependencies", pip_step)

    result = interface._setup_python_project(
        tmp_path, virtual_env=True, install_deps=install_deps, use_uv=True
    )

    assert uv_calls == [install_deps]
    assert result["tools_configured"] == expected_tools
    assert result["warnings"] == []


def test_setup_python_reports_a_missing_uv_as_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()

    def uv_setup(_path: Path, _deps: bool) -> ProjectCreationResult:
        raise OSError("uv is not installed")

    monkeypatch.setattr(interface._python_service, "setup_uv_environment", uv_setup)

    result = interface._setup_python_project(
        tmp_path, virtual_env=True, install_deps=True, use_uv=True
    )

    assert result["tools_configured"] == []
    assert result["warnings"] == ["uv environment setup skipped: uv is not installed"]


@pytest.mark.parametrize(("has_lock", "expected"), [(True, True), (False, False)])
def test_setup_project_detects_uv_from_the_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    has_lock: bool,
    expected: bool,
) -> None:
    if has_lock:
        (tmp_path / "uv.lock").touch()
    interface = ProjectSetupInterface()
    captured: dict[str, object] = {}
    monkeypatch.setattr(interface, "_check_dependencies", lambda _type: "")
    monkeypatch.setattr(
        interface, "_copy_vscode_config", lambda *_args, **_kwargs: None
    )

    def setup_python(*_args: object, **kwargs: object) -> dict[str, list[str]]:
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(interface, "_setup_python_project", setup_python)

    interface.setup_project(tmp_path, "python")

    assert captured["use_uv"] is expected


# ///////////////////////////////////////////////////////////////
# JAVASCRIPT ORCHESTRATION
# ///////////////////////////////////////////////////////////////


def test_setup_javascript_runs_each_requested_operation_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()
    calls: list[str] = []

    def succeed(name: str):
        def operation(*_args: object) -> ProjectCreationResult:
            calls.append(name)
            return ProjectCreationResult(success=True)

        return operation

    monkeypatch.setattr(
        interface._javascript_service,
        "install_dependencies",
        succeed("dependencies"),
    )
    monkeypatch.setattr(
        interface._javascript_service,
        "setup_git_repository",
        succeed("git"),
    )

    result = interface._setup_javascript_project(
        tmp_path,
        "react",
        install_deps=True,
        setup_git_hooks=True,
    )

    assert calls == ["dependencies", "git"]
    assert result["tools_configured"] == calls
    assert result["warnings"] == []


def test_setup_javascript_collects_unsuccessful_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interface = ProjectSetupInterface()

    def failure(*_args: object) -> ProjectCreationResult:
        return ProjectCreationResult(success=False)

    monkeypatch.setattr(interface._javascript_service, "install_dependencies", failure)
    monkeypatch.setattr(interface._javascript_service, "setup_git_repository", failure)

    result = interface._setup_javascript_project(
        tmp_path,
        "vue",
        install_deps=True,
        setup_git_hooks=True,
    )

    assert result["tools_configured"] == []
    assert result["warnings"] == [
        "Dependency installation failed",
        "Git repository setup failed",
    ]


# ///////////////////////////////////////////////////////////////
# SUPPORT HELPERS
# ///////////////////////////////////////////////////////////////


@pytest.mark.parametrize(
    "language",
    [
        "python",
        "javascript",
    ],
)
def test_copy_vscode_config_renders_from_copier_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    language: str,
) -> None:
    def render(_self, request):  # noqa: ANN001
        source = request.destination / ".vscode"
        source.mkdir(parents=True)
        (source / "settings.json").write_text("{}")
        return request.destination

    monkeypatch.setattr(
        "womm.interfaces.project.setup_interface.CopierProjectCreationService.create",
        render,
    )

    ProjectSetupInterface()._copy_vscode_config(
        tmp_path,
        SetupProfile(language=language, template_source=tmp_path, answers={}),
    )

    assert (tmp_path / ".vscode" / "settings.json").read_text() == "{}"


def test_copy_vscode_config_uses_template_answers_for_javascript_variant(
    tmp_path: Path,
) -> None:
    profile = resolve_setup_profile("javascript")
    assert profile is not None
    project = tmp_path / "vue-project"
    project.mkdir()

    ProjectSetupInterface()._copy_vscode_config(
        project,
        profile,
        template_answers={"framework": "vue", "typescript": True},
    )

    settings = json.loads((project / ".vscode/settings.json").read_text())
    extensions = json.loads((project / ".vscode/extensions.json").read_text())
    assert settings["editor.defaultFormatter"] == "esbenp.prettier-vscode"
    assert "vue.volar" in extensions["recommendations"]


def test_copy_vscode_config_keeps_default_javascript_variant(tmp_path: Path) -> None:
    profile = resolve_setup_profile("javascript")
    assert profile is not None
    project = tmp_path / "plain-project"
    project.mkdir()

    ProjectSetupInterface()._copy_vscode_config(project, profile)

    settings = json.loads((project / ".vscode/settings.json").read_text())
    assert settings["editor.defaultFormatter"] == "biomejs.biome"


@pytest.mark.parametrize("venv_name", [".venv", "venv"])
def test_vscode_uses_real_project_name_and_environment(
    tmp_path: Path, venv_name: str
) -> None:
    template = tmp_path / "template"
    settings = template / "content" / ".vscode"
    settings.mkdir(parents=True)
    (template / "copier.yml").write_text(
        "_subdirectory: content\nproject_name:\n  type: str\n", encoding="utf-8"
    )
    (settings / "settings.json.jinja").write_text(
        '{"python.analysis.extraPaths": ["src/{{ project_name }}"], '
        '"python.defaultInterpreterPath": "${workspaceFolder}/.venv"}',
        encoding="utf-8",
    )
    project = tmp_path / "real-project"
    (project / venv_name).mkdir(parents=True)
    profile = SetupProfile(language="python", template_source=template, answers={})

    ProjectSetupInterface()._copy_vscode_config(
        project,
        profile,
        template_answers={"project_name": "wrong"},
    )

    config = json.loads((project / ".vscode/settings.json").read_text())
    assert config["python.analysis.extraPaths"] == ["src/real-project"]
    assert (
        config["python.defaultInterpreterPath"] == f"${{workspaceFolder}}/{venv_name}"
    )


@pytest.mark.parametrize(
    ("language", "runtime"),
    [
        ("python", "python"),
        ("javascript", "node"),
    ],
)
def test_check_dependencies_probes_expected_runtime(
    monkeypatch: pytest.MonkeyPatch,
    language: str,
    runtime: str,
) -> None:
    captured: list[str] = []

    def successful_probe(name: str) -> SimpleNamespace:
        captured.append(name)
        return SimpleNamespace(success=True)

    monkeypatch.setattr(
        "womm.interfaces.project.setup_interface.probe", successful_probe
    )

    error = ProjectSetupInterface()._check_dependencies(
        SetupProfile(language=language, template_source=Path(), answers={})
    )

    assert error == ""
    assert captured == [runtime]


def test_check_dependencies_translates_probe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_probe(_name: str) -> SimpleNamespace:
        raise OSError("probe unavailable")

    monkeypatch.setattr("womm.interfaces.project.setup_interface.probe", fail_probe)

    error = ProjectSetupInterface()._check_dependencies(
        SetupProfile(language="python", template_source=Path(), answers={})
    )

    assert error == "Error checking dependencies: probe unavailable"


def test_vscode_config_survives_a_folder_name_the_template_refuses(
    tmp_path: Path,
) -> None:
    from womm.services.project.setup_profile_resolver import resolve_setup_profile

    project = tmp_path / "My Project"
    project.mkdir()
    profile = resolve_setup_profile("python")
    assert profile is not None

    ProjectSetupInterface()._copy_vscode_config(project, profile)

    assert (project / ".vscode" / "settings.json").is_file()
