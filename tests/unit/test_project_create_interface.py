"""Tests for the Copier-backed project creation interface."""

from pathlib import Path
from unittest.mock import patch

import pytest

from womm.interfaces.project.create_interface import ProjectCreateInterface
from womm.shared.results import ProjectSetupResult


def test_create_preserves_partial_setup_warnings(tmp_path: Path):
    with patch(
        "womm.interfaces.project.setup_interface.ProjectSetupInterface.setup_project",
        return_value=ProjectSetupResult(
            success=True, project_path=tmp_path, warnings=["Dependencies failed"]
        ),
    ):
        assert ProjectCreateInterface()._run_setup(tmp_path, "python") == [
            "Dependencies failed"
        ]


def test_create_project_returns_a_successful_result(tmp_path: Path):
    interface = ProjectCreateInterface()

    result = interface.create_project(
        template="official/python",
        destination=tmp_path / "acme",
        answers={"project_name": "acme", "package_name": "acme"},
        force=False,
        pretend=False,
        defaults=True,
        setup=False,
    )

    assert result.success is True
    assert result.project_path == tmp_path / "acme"
    assert (tmp_path / "acme" / "pyproject.toml").is_file()


def test_unknown_template_yields_a_failed_result(tmp_path: Path):
    interface = ProjectCreateInterface()

    result = interface.create_project(
        template="nope",
        destination=tmp_path / "acme",
        answers={},
        force=False,
        pretend=False,
        defaults=True,
        setup=False,
    )

    assert result.success is False
    assert "nope" in result.error


def test_non_empty_destination_yields_a_failed_result(tmp_path: Path):
    destination = tmp_path / "acme"
    destination.mkdir()
    (destination / "keep.txt").write_text("x", encoding="utf-8")
    interface = ProjectCreateInterface()

    result = interface.create_project(
        template="official/python",
        destination=destination,
        answers={"project_name": "acme"},
        force=False,
        pretend=False,
        defaults=True,
        setup=False,
    )

    assert result.success is False
    assert "--force" in result.error


def test_setup_is_not_run_by_default(tmp_path: Path):
    interface = ProjectCreateInterface()

    with patch(
        "womm.interfaces.project.setup_interface.ProjectSetupInterface.setup_project"
    ) as setup:
        interface.create_project(
            template="official/python",
            destination=tmp_path / "acme",
            answers={"project_name": "acme", "package_name": "acme"},
            force=False,
            pretend=False,
            defaults=True,
            setup=False,
        )

    setup.assert_not_called()


def test_setup_flag_delegates_to_the_setup_interface(tmp_path: Path):
    interface = ProjectCreateInterface()

    with patch(
        "womm.interfaces.project.setup_interface.ProjectSetupInterface.setup_project"
    ) as setup:
        interface.create_project(
            template="official/python",
            destination=tmp_path / "acme",
            answers={"project_name": "acme", "package_name": "acme"},
            force=False,
            pretend=False,
            defaults=True,
            setup=True,
        )

    setup.assert_called_once()


def test_create_project_with_setup_resolves_through_the_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """entry.id ("python") must resolve via the catalog-backed resolver,
    not a fixed SUPPORTED_PROJECT_TYPES list."""
    from womm.services.project import setup_profile_resolver

    captured: dict[str, object] = {}

    def fake_setup_project(self, project_path, **kwargs):  # noqa: ANN001, ARG001
        captured["project_path"] = project_path
        captured.update(kwargs)
        from womm.shared.results import ProjectSetupResult

        return ProjectSetupResult(success=True, project_path=project_path)

    monkeypatch.setattr(
        "womm.interfaces.project.setup_interface.ProjectSetupInterface.setup_project",
        fake_setup_project,
    )

    interface = ProjectCreateInterface()
    result = interface.create_project(
        "python",
        tmp_path / "generated",
        answers={"project_name": "generated"},
        defaults=True,
        setup=True,
    )

    assert result.success
    assert captured["project_type"] == "python"
    assert setup_profile_resolver.resolve_setup_profile("python") is not None


def test_pretend_reports_success_without_writing(tmp_path: Path):
    interface = ProjectCreateInterface()

    result = interface.create_project(
        template="official/python",
        destination=tmp_path / "acme",
        answers={"project_name": "acme", "package_name": "acme"},
        force=False,
        pretend=True,
        defaults=True,
        setup=False,
    )

    assert result.success is True
    assert not (tmp_path / "acme" / "pyproject.toml").exists()
