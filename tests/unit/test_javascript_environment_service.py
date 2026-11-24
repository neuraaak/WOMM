#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST JAVASCRIPT ENVIRONMENT SERVICE - Direct service coverage
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""Direct tests for JavaScript environment setup operations."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
from pathlib import Path
from types import SimpleNamespace

# Third-party imports
import pytest

# Local imports
from womm.exceptions.project import ProjectServiceError
from womm.services.project.javascript_environment_service import (
    JavaScriptEnvironmentService,
)

# ///////////////////////////////////////////////////////////////
# FIXTURES AND HELPERS
# ///////////////////////////////////////////////////////////////


@pytest.fixture
def service() -> JavaScriptEnvironmentService:
    """Return the shared JavaScript environment service."""
    return JavaScriptEnvironmentService()


# ///////////////////////////////////////////////////////////////
# DEPENDENCIES
# ///////////////////////////////////////////////////////////////


@pytest.mark.parametrize("project_type", ["node", "javascript", "react", "vue"])
def test_install_dependencies_accepts_javascript_variants(
    tmp_path: Path,
    service: JavaScriptEnvironmentService,
    monkeypatch: pytest.MonkeyPatch,
    project_type: str,
) -> None:
    monkeypatch.setattr(
        "womm.services.project.javascript_environment_service.install_javascript_dependencies",
        lambda _path: "pnpm",
    )

    result = service.install_dependencies(tmp_path, project_type)

    assert result.success
    assert result.project_type == project_type
    assert result.message == "Dependencies installed with pnpm"


def test_install_dependencies_wraps_install_failure(
    tmp_path: Path,
    service: JavaScriptEnvironmentService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_path: Path) -> str:
        raise RuntimeError("npm install failed: boom")

    monkeypatch.setattr(
        "womm.services.project.javascript_environment_service.install_javascript_dependencies",
        fail,
    )

    with pytest.raises(ProjectServiceError) as excinfo:
        service.install_dependencies(tmp_path, "node")

    assert excinfo.value.operation == "install_dependencies"
    assert excinfo.value.reason == "npm install failed: boom"


# ///////////////////////////////////////////////////////////////
# GIT
# ///////////////////////////////////////////////////////////////


def test_setup_git_repository_skips_when_git_is_unavailable(
    tmp_path: Path,
    service: JavaScriptEnvironmentService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _command: None)

    result = service.setup_git_repository(tmp_path)

    assert result.success
    assert result.warnings == ["Git not found in system PATH"]


@pytest.mark.parametrize(
    ("returncode", "expected_success"),
    [(0, True), (1, False)],
)
def test_setup_git_repository_reports_command_result(
    tmp_path: Path,
    service: JavaScriptEnvironmentService,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    expected_success: bool,
) -> None:
    (tmp_path / "package.json").touch()
    monkeypatch.setattr("shutil.which", lambda _command: "git")
    monkeypatch.setattr(
        service._command_runner,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=returncode, stderr="git failed"
        ),
    )

    result = service.setup_git_repository(tmp_path)

    assert result.success is expected_success
    assert result.error == ("" if expected_success else "git failed")
