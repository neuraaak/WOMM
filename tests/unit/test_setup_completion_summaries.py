"""Tests for the setup completion panel."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from womm.shared.results import ProjectSetupResult
from womm.ui.project.setup import setup_completion_summaries as summaries


def _render(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, warnings: list[str]
) -> tuple[str, str, MagicMock]:
    ezconsole, ezprinter = MagicMock(), MagicMock()
    monkeypatch.setattr(summaries, "ezconsole", ezconsole)
    monkeypatch.setattr(summaries, "ezprinter", ezprinter)
    summaries.print_project_setup_result(
        ProjectSetupResult(
            success=True,
            project_path=tmp_path,
            project_type="python",
            tools_configured=["git"],
            warnings=warnings,
        )
    )
    panel = ezconsole.print.call_args_list[-1].args[0]
    return str(panel.title), str(panel.renderable), ezprinter


def test_panel_reports_completion_without_warnings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    title, body, _ = _render(monkeypatch, tmp_path, [])

    assert "Completed!" in title
    assert "did not complete" not in body


def test_panel_is_incomplete_when_a_step_failed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    title, body, ezprinter = _render(
        monkeypatch,
        tmp_path,
        ["uv environment setup skipped", "Git hooks not installed"],
    )

    assert "Incomplete" in title and "Completed" not in title
    assert "2 warning(s)" in body
    assert ezprinter.warning.call_count == 2
