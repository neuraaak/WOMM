#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST PROJECT ENV UTILS - Environment setup utilities coverage
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""Direct tests for virtual environment and npm dependency utilities."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import os
from pathlib import Path

# Third-party imports
import pytest

# Local imports
from womm.services.common.command_runner_service import CommandRunnerService
from womm.services.project import env_utils
from womm.shared.results.base import CommandResult

# ///////////////////////////////////////////////////////////////
# HELPERS
# ///////////////////////////////////////////////////////////////


def _fake_venv_create(venv_path: Path, **_kwargs: object) -> None:
    venv_path.mkdir(parents=True)


def _make_venv(venv_path: Path) -> Path:
    scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
    scripts.mkdir(parents=True)
    (scripts / ("python.exe" if os.name == "nt" else "python")).touch()
    pip_exe = scripts / ("pip.exe" if os.name == "nt" else "pip")
    pip_exe.touch()
    return pip_exe


def _patch_command_runner(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    """Patch the CommandRunnerService singleton instance's ``run`` method.

    Patched on the instance (not the class): the singleton persists across
    the whole test session, and other tests in the suite shadow ``run`` on
    that same instance, which would otherwise mask a class-level patch.
    """
    monkeypatch.setattr(CommandRunnerService(), "run", handler)


# ///////////////////////////////////////////////////////////////
# CREATE VIRTUAL ENVIRONMENT
# ///////////////////////////////////////////////////////////////


def test_create_virtual_environment_reports_existing_venv(tmp_path: Path) -> None:
    (tmp_path / "venv").mkdir()

    result = env_utils.create_virtual_environment(tmp_path)

    assert result == {
        "success": True,
        "venv_path": str(tmp_path / "venv"),
        "existing": True,
    }


def test_new_environment_uses_copier_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(env_utils.venv, "create", _fake_venv_create)
    result = env_utils.create_virtual_environment(tmp_path)
    assert result["venv_path"] == str(tmp_path / ".venv")


def test_create_virtual_environment_creates_new_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(env_utils.venv, "create", _fake_venv_create)

    result = env_utils.create_virtual_environment(tmp_path, venv_name="myenv")

    assert result == {
        "success": True,
        "venv_path": str(tmp_path / "myenv"),
        "existing": False,
    }
    assert (tmp_path / "myenv").is_dir()


def test_create_virtual_environment_upgrades_pip_when_executables_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def create_with_executables(venv_path: Path, **_kwargs: object) -> None:
        _make_venv(venv_path)

    monkeypatch.setattr(env_utils.venv, "create", create_with_executables)
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **_kwargs: object):
        captured["command"] = command
        return CommandResult(returncode=0)

    _patch_command_runner(monkeypatch, fake_run)

    env_utils.create_virtual_environment(tmp_path)

    assert captured["command"][-4:] == ["-m", "pip", "install", "--upgrade", "pip"][-4:]
    assert "pip" in captured["command"][2]


# ///////////////////////////////////////////////////////////////
# FIND EXECUTABLES
# ///////////////////////////////////////////////////////////////


def test_find_pip_executable_returns_path_when_present(tmp_path: Path) -> None:
    expected = _make_venv(tmp_path)

    pip_exe = env_utils.find_pip_executable(tmp_path)

    assert pip_exe == expected


def test_find_pip_executable_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="pip not found"):
        env_utils.find_pip_executable(tmp_path)


# ///////////////////////////////////////////////////////////////
# INSTALL PYTHON DEPENDENCIES
# ///////////////////////////////////////////////////////////////


def test_install_python_dependencies_raises_when_venv_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="Virtual environment not found"):
        env_utils.install_python_dependencies(tmp_path)


def test_install_python_dependencies_skips_when_requirements_file_missing(
    tmp_path: Path,
) -> None:
    _make_venv(tmp_path / "venv")

    result = env_utils.install_python_dependencies(tmp_path)

    assert result is True


def test_install_python_dependencies_installs_from_requirements_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_venv(tmp_path / "venv")
    (tmp_path / "requirements-dev.txt").write_text("pytest\n")
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **_kwargs: object):
        captured["command"] = command
        return CommandResult(returncode=0)

    _patch_command_runner(monkeypatch, fake_run)

    result = env_utils.install_python_dependencies(tmp_path)

    assert result is True
    assert captured["command"][1:] == ["install", "-r", "requirements-dev.txt"]


def test_install_python_dependencies_raises_on_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_venv(tmp_path / "venv")
    (tmp_path / "requirements-dev.txt").write_text("pytest\n")
    _patch_command_runner(
        monkeypatch, lambda *_a, **_k: CommandResult(returncode=1, stderr="boom")
    )

    with pytest.raises(RuntimeError, match="Failed to install dependencies"):
        env_utils.install_python_dependencies(tmp_path)


def test_install_python_dependencies_uses_alt_venv_dir(tmp_path: Path) -> None:
    _make_venv(tmp_path / ".venv")

    result = env_utils.install_python_dependencies(tmp_path)

    assert result is True


# ///////////////////////////////////////////////////////////////
# DETECT PACKAGE MANAGER
# ///////////////////////////////////////////////////////////////


def test_detect_package_manager_defaults_to_npm(tmp_path: Path) -> None:
    assert env_utils.detect_package_manager(tmp_path) == "npm"


@pytest.mark.parametrize(
    ("lockfile", "expected"),
    [
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
    ],
)
def test_detect_package_manager_reads_the_lockfile(
    tmp_path: Path, lockfile: str, expected: str
) -> None:
    (tmp_path / lockfile).touch()

    assert env_utils.detect_package_manager(tmp_path) == expected


def test_detect_package_manager_prefers_the_package_json_field(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"packageManager": "pnpm@10.0.0"}', encoding="utf-8"
    )
    (tmp_path / "yarn.lock").touch()

    assert env_utils.detect_package_manager(tmp_path) == "pnpm"


@pytest.mark.parametrize(
    "manifest",
    ['{"packageManager": "evil@1.0.0"}', "[]", "not json"],
)
def test_detect_package_manager_ignores_an_unusable_field(
    tmp_path: Path, manifest: str
) -> None:
    (tmp_path / "package.json").write_text(manifest, encoding="utf-8")
    (tmp_path / "yarn.lock").touch()

    assert env_utils.detect_package_manager(tmp_path) == "yarn"


# ///////////////////////////////////////////////////////////////
# INSTALL JAVASCRIPT DEPENDENCIES
# ///////////////////////////////////////////////////////////////


def test_install_javascript_dependencies_raises_when_manager_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "bun.lock").touch()
    monkeypatch.setattr(env_utils.shutil, "which", lambda _name: None)

    with pytest.raises(FileNotFoundError, match="bun is not installed"):
        env_utils.install_javascript_dependencies(tmp_path)


def test_install_javascript_dependencies_runs_the_resolved_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # On Windows, which() resolves pnpm to its .CMD shim, which must be run.
    (tmp_path / "pnpm-lock.yaml").touch()
    resolved = "/opt/nodejs/pnpm.CMD"
    monkeypatch.setattr(
        env_utils.shutil, "which", lambda name: resolved if name == "pnpm" else None
    )
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **_kwargs: object):
        captured["command"] = command
        return CommandResult(returncode=0)

    _patch_command_runner(monkeypatch, fake_run)

    assert env_utils.install_javascript_dependencies(tmp_path) == "pnpm"
    assert captured["command"] == [resolved, "install"]


def test_install_javascript_dependencies_raises_on_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(env_utils.shutil, "which", lambda _name: "/usr/bin/npm")
    _patch_command_runner(
        monkeypatch, lambda *_a, **_k: CommandResult(returncode=1, stderr="boom")
    )

    with pytest.raises(RuntimeError, match="npm install failed: boom"):
        env_utils.install_javascript_dependencies(tmp_path)
