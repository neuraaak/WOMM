"""User-facing guidance of `womm setup`: opt-in steps and visible flags."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from womm.cli import womm
from womm.commands.project.setup import setup_javascript, setup_python
from womm.shared.results import ProjectCreationResult
from womm.ui.project.create import create_completion_summaries
from womm.ui.project.setup import setup_completion_summaries
from womm.ui.project.setup.setup_completion_summaries import SETUP_STEP_FLAGS

# Options that select no setup step.
NON_STEP_OPTIONS = {"project_path", "interactive", "verbose", "help", "project_type"}


def _python_project(path: Path) -> Path:
    (path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0"\n', encoding="utf-8"
    )
    return path


@pytest.fixture
def printed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture what the setup summaries print, whatever console they bind."""
    lines: list[str] = []

    def record(*renderables: object, **_kwargs: object) -> None:
        for renderable in renderables:
            lines.append(str(getattr(renderable, "renderable", renderable)))

    monkeypatch.setattr(setup_completion_summaries.ezconsole, "print", record)
    return lines


@pytest.mark.parametrize(
    ("language", "command"),
    [("python", setup_python), ("javascript", setup_javascript)],
)
def test_the_hint_lists_exactly_the_step_flags_of_the_command(
    language: str, command: click.Command
) -> None:
    flags = [
        param.opts[-1]
        for param in command.params
        if isinstance(param, click.Option) and param.name not in NON_STEP_OPTIONS
    ]

    assert flags == [flag for flag, _description in SETUP_STEP_FLAGS[language]]


@pytest.mark.parametrize("subcommand", ["python", "detect"])
def test_setup_without_flags_writes_nothing_and_shows_the_flags(
    tmp_path: Path, printed: list[str], subcommand: str
) -> None:
    project = _python_project(tmp_path)

    result = CliRunner().invoke(womm, ["setup", subcommand, "-p", str(project)])

    assert result.exit_code == 0, result.output
    assert sorted(path.name for path in project.iterdir()) == ["pyproject.toml"]
    hint = "\n".join(printed)
    assert "nothing was changed" in hint
    for flag, _description in SETUP_STEP_FLAGS["python"]:
        assert flag in hint


def test_setup_vscode_flag_writes_the_vscode_configuration(
    tmp_path: Path, printed: list[str]
) -> None:
    project = _python_project(tmp_path)

    result = CliRunner().invoke(
        womm, ["setup", "python", "-p", str(project), "--setup-vscode"]
    )

    assert result.exit_code == 0, result.output
    assert (project / ".vscode" / "settings.json").is_file()
    assert "VS Code configuration written" in "\n".join(printed)


def test_every_command_accepts_short_help() -> None:
    def walk(command: click.Command, path: list[str]):
        yield path
        if isinstance(command, click.Group):
            for name, sub in command.commands.items():
                yield from walk(sub, [*path, name])

    for path in walk(womm, []):
        result = CliRunner().invoke(womm, [*path, "-h"])
        assert result.exit_code == 0, f"womm {' '.join(path)} -h: {result.output}"


@pytest.mark.parametrize("suggest_setup", [True, False])
def test_create_points_to_setup_only_when_it_did_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suggest_setup: bool
) -> None:
    infos: list[str] = []
    monkeypatch.setattr(
        create_completion_summaries.ezprinter,
        "info",
        lambda message: infos.append(message),
    )
    monkeypatch.setattr(
        create_completion_summaries.ezprinter, "success", lambda _message: None
    )

    create_completion_summaries.render_project_creation_result(
        ProjectCreationResult(success=True, project_path=tmp_path),
        suggest_setup=suggest_setup,
    )

    assert any("womm setup detect" in info for info in infos) is suggest_setup
