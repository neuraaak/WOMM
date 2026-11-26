#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST UPDATE SERVICE - PyPI Release Check
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""Tests for the cached PyPI release check and the CLI update notice."""

from __future__ import annotations

# Standard library imports
import json

# Third-party imports
import pytest
from click.testing import CliRunner

# Local imports
from womm import cli
from womm.cli import womm
from womm.services.system import update_service

_DAY = 24 * 60 * 60
_NOW = 1_000_000_000.0


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolate the data directory, hence the cache file."""
    monkeypatch.setenv("WOMM_HOME", str(tmp_path))
    return tmp_path


class _FakeFetch:
    """Stand-in for the network call; ``answer`` is what PyPI returns."""

    def __init__(self) -> None:
        self.answer: str | None = "9.0.0"
        self.calls = 0

    def __call__(self) -> str | None:
        self.calls += 1
        return self.answer


@pytest.fixture
def fetches(monkeypatch) -> _FakeFetch:
    fetch = _FakeFetch()
    monkeypatch.setattr(update_service, "_fetch_latest", fetch)
    return fetch


def _write_cache(home, **data) -> None:
    (home / "update-check.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("5.2.0", "5.1.1", True),
        ("5.10.0", "5.9.0", True),
        ("5.1.1", "5.1.1", False),
        ("5.1.0", "5.1.1", False),
        ("6.0.0rc1", "5.1.1", False),
        ("5.2.0", "5.2.0.dev1", False),
    ],
)
def test_is_newer_compares_final_releases_only(candidate, current, expected):
    assert update_service.is_newer(candidate, current) is expected


def test_a_fresh_cache_answers_without_the_network(home, fetches):
    _write_cache(home, checked_at=_NOW - 60, latest="5.2.0")

    update = update_service.check_for_update("5.1.1", now=_NOW)

    assert update is not None
    assert update.latest == "5.2.0"
    assert fetches.calls == 0


def test_a_stale_cache_is_refreshed_and_rewritten(home, fetches):
    _write_cache(home, checked_at=_NOW - _DAY - 1, latest="5.1.1")

    update = update_service.check_for_update("5.1.1", now=_NOW)

    assert update is not None
    assert update.latest == "9.0.0"
    assert fetches.calls == 1
    cache = json.loads((home / "update-check.json").read_text(encoding="utf-8"))
    assert cache == {"checked_at": _NOW, "latest": "9.0.0"}


def test_a_failed_fetch_keeps_the_last_release_and_waits_a_day(home, fetches):
    fetches.answer = None
    _write_cache(home, checked_at=_NOW - _DAY - 1, latest="5.2.0")

    update = update_service.check_for_update("5.1.1", now=_NOW)
    update_service.check_for_update("5.1.1", now=_NOW + 60)

    assert update is not None
    assert update.latest == "5.2.0"
    assert fetches.calls == 1


@pytest.mark.parametrize("content", ["not json", "[1, 2]", '{"checked_at": "x"}'])
def test_an_unreadable_cache_counts_as_stale(home, fetches, content):
    (home / "update-check.json").write_text(content, encoding="utf-8")

    update = update_service.check_for_update("5.1.1", now=_NOW)

    assert update is not None
    assert fetches.calls == 1


@pytest.mark.usefixtures("home")
def test_no_update_when_the_installed_version_is_the_latest(fetches):
    fetches.answer = "5.1.1"

    assert update_service.check_for_update("5.1.1", now=_NOW) is None


@pytest.mark.usefixtures("home")
def test_offline_without_cache_reports_nothing(fetches):
    fetches.answer = None

    assert update_service.check_for_update("5.1.1", now=_NOW) is None


@pytest.mark.parametrize(
    ("prefix", "command"),
    [
        (r"C:\Users\me\AppData\Roaming\uv\tools\womm-cli", "uv tool upgrade womm-cli"),
        ("/home/me/.local/share/uv/tools/womm-cli", "uv tool upgrade womm-cli"),
        ("/home/me/.local/pipx/venvs/womm-cli", "pipx upgrade womm-cli"),
        ("/home/me/project/.venv", "python -m pip install --upgrade womm-cli"),
    ],
)
def test_upgrade_command_follows_the_installation(monkeypatch, prefix, command):
    monkeypatch.setattr(update_service.sys, "prefix", prefix)

    assert update_service.upgrade_command() == command


# ///////////////////////////////////////////////////////////////
# CLI NOTICE
# ///////////////////////////////////////////////////////////////


def _notice_for(monkeypatch, latest: str | None) -> str:
    monkeypatch.setattr(cli, "_update_check_enabled", lambda: True)
    monkeypatch.setattr(
        update_service,
        "check_for_update",
        lambda current: (
            update_service.UpdateInfo(current, latest, "uv tool upgrade womm-cli")
            if latest
            else None
        ),
    )
    return CliRunner().invoke(womm, ["deps"]).stderr


def test_the_cli_prints_the_notice_after_the_command(monkeypatch):
    notice = _notice_for(monkeypatch, "9.0.0")

    assert "WOMM 9.0.0 is available" in notice
    assert "uv tool upgrade womm-cli" in notice


def test_the_cli_stays_silent_without_an_update(monkeypatch):
    assert _notice_for(monkeypatch, None) == ""


@pytest.mark.parametrize(
    ("variables", "tty", "expected"),
    [
        ({}, True, True),
        ({}, False, False),
        ({"WOMM_NO_UPDATE_CHECK": "1"}, True, False),
        ({"CI": "true"}, True, False),
    ],
)
def test_the_check_runs_only_for_a_person_at_a_terminal(
    monkeypatch, variables, tty, expected
):
    monkeypatch.delenv("WOMM_NO_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("CI", raising=False)
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(cli.sys.stderr, "isatty", lambda: tty, raising=False)

    assert cli._update_check_enabled() is expected


# ///////////////////////////////////////////////////////////////
# WELCOME SCREEN STATUS
# ///////////////////////////////////////////////////////////////


def _welcome_with(monkeypatch, latest: str | None) -> str:
    reported: list[None] = []
    monkeypatch.setattr(cli, "_update_check_enabled", lambda: True)
    monkeypatch.setattr(cli, "_report_update", lambda: reported.append(None))
    monkeypatch.setattr(update_service, "latest_release", lambda: latest)
    monkeypatch.setattr(cli, "__version__", "5.1.1")

    result = CliRunner().invoke(womm, [])

    assert result.exit_code == 0
    # The welcome screen shows the status itself: no second notice.
    assert reported == []
    return result.output


def test_welcome_shows_an_available_update(monkeypatch):
    output = _welcome_with(monkeypatch, "9.0.0")

    assert "WOMM 9.0.0 is available (installed: 5.1.1)" in output
    assert "Upgrade with:" in output


@pytest.mark.parametrize("latest", ["5.1.1", "5.1.0"])
def test_welcome_says_when_womm_is_up_to_date(monkeypatch, latest):
    assert "WOMM 5.1.1 is up to date." in _welcome_with(monkeypatch, latest)


def test_welcome_says_when_pypi_cannot_be_reached(monkeypatch):
    assert "PyPI could not be reached" in _welcome_with(monkeypatch, None)


def test_welcome_without_update_check_does_not_reach_pypi(monkeypatch):
    def fail() -> None:
        raise AssertionError("PyPI must not be queried")

    monkeypatch.setattr(cli, "_update_check_enabled", lambda: False)
    monkeypatch.setattr(update_service, "latest_release", fail)

    result = CliRunner().invoke(womm, [])

    assert result.exit_code == 0
    assert "(update check skipped)" in result.output
