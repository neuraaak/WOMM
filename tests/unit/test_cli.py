#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST CLI - Command Registration
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""Regression tests for the unconditional CLI command surface."""

from __future__ import annotations

# Standard library imports
import os
import subprocess
import sys

# Third-party imports
from click.testing import CliRunner

# Local imports
from womm import cli
from womm.cli import womm


def test_windows_console_configuration_uses_utf8(monkeypatch) -> None:
    configured_encodings: list[str] = []

    class Stream:
        def reconfigure(self, *, encoding: str) -> None:
            configured_encodings.append(encoding)

    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setattr(cli.sys, "stdout", Stream())
    monkeypatch.setattr(cli.sys, "stderr", Stream())
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")

    cli._configure_windows_console()

    assert configured_encodings == ["utf-8", "utf-8"]
    assert cli.os.environ["PYTHONIOENCODING"] == "utf-8"


def test_help_registers_all_operational_command_groups() -> None:
    result = CliRunner().invoke(womm, ["--help"])

    assert result.exit_code == 0
    for command in (
        "doctor",
        "path",
        "create",
        "system",
        "context",
        "setup",
        "template",
        "deps",
    ):
        assert command in result.output


def test_removed_log_options_are_rejected() -> None:
    runner = CliRunner()
    for option in ("--log-level=debug", "--log-file=out.log", "--log-json"):
        result = runner.invoke(womm, [option, "--help"])
        assert result.exit_code != 0
        assert "No such option" in result.output


def test_help_loads_without_windows_registry(tmp_path) -> None:
    environment = os.environ.copy()
    environment["WOMM_HOME"] = str(tmp_path / "womm-home")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['winreg'] = None; "
            "from click.testing import CliRunner; "
            "from womm.cli import womm; "
            "raise SystemExit(CliRunner().invoke(womm, ['--help']).exit_code)",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_help_does_not_expose_removed_self_installation_commands() -> None:
    result = CliRunner().invoke(womm, ["--help"])

    assert result.exit_code == 0
    assert "install" not in womm.commands
    assert "uninstall" not in womm.commands


def test_doctor_reports_runtime_without_creating_data_directory(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "womm-home"
    monkeypatch.setenv("WOMM_HOME", str(data_dir))
    monkeypatch.setattr(
        "womm.interfaces.core.doctor_interface.DoctorInterface._context_menu_status",
        staticmethod(lambda: "0 entries"),
    )

    result = CliRunner().invoke(womm, ["doctor"])

    assert result.exit_code == 0
    # The logger, loaded by the command itself, owns logs/; doctor writes
    # nothing else under the data directory.
    written = {path.name for path in data_dir.iterdir()} if data_dir.exists() else set()
    assert written <= {"logs"}


def test_doctor_diagnose_reports_the_data_directory(tmp_path, monkeypatch) -> None:
    from womm.interfaces.core import DoctorInterface

    data_dir = tmp_path / "womm-home"
    monkeypatch.setenv("WOMM_HOME", str(data_dir))
    monkeypatch.setattr(
        "womm.interfaces.core.doctor_interface.DoctorInterface._context_menu_status",
        staticmethod(lambda: "0 entries"),
    )

    result = DoctorInterface().diagnose()

    assert result.success
    assert result.data_dir == str(data_dir)
    assert result.context_menu_status == "0 entries"
    assert not data_dir.exists()


def test_create_parses_repeated_data_options():
    from womm.commands.project.create import parse_data_options

    assert parse_data_options(("a=1", "b=two")) == {"a": "1", "b": "two"}


def test_create_rejects_a_malformed_data_option():
    import click
    import pytest

    from womm.commands.project.create import parse_data_options

    with pytest.raises(click.BadParameter):
        parse_data_options(("novalue",))


def test_create_keeps_equals_signs_in_values():
    from womm.commands.project.create import parse_data_options

    assert parse_data_options(("k=a=b",)) == {"k": "a=b"}


def test_create_help_lists_the_generic_arguments():
    from click.testing import CliRunner

    from womm.commands.project.create import create_command

    result = CliRunner().invoke(create_command, ["--help"])

    assert result.exit_code == 0
    assert "TEMPLATE" in result.output
    assert "--setup" in result.output


def test_version_option_reports_the_public_package_version() -> None:
    import womm as womm_package

    result = CliRunner().invoke(womm, ["--version"])

    assert result.exit_code == 0
    assert womm_package.__version__ in result.output


# Help, usage and `--version` must not pay for these: each costs 100-600 ms.
_HEAVY_MODULES = (
    "copier",
    "InquirerPy",
    "prompt_toolkit",
    "ezplog",
    "loguru",
    "womm.interfaces",
    "womm.services",
)


def _modules_loaded_by(code: str) -> set[str]:
    """Run ``code`` in a fresh interpreter and return the heavy modules it loaded."""
    probe = (
        f"{code}\n"
        "import sys\n"
        f"print(','.join(m for m in {_HEAVY_MODULES!r} if m in sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(filter(None, result.stdout.splitlines()[-1].split(",")))


def test_importing_the_cli_loads_no_heavy_module() -> None:
    assert _modules_loaded_by("import womm.cli") == set()


def test_bare_group_help_loads_no_heavy_module() -> None:
    code = (
        "from click.testing import CliRunner\n"
        "from womm.cli import womm\n"
        "for args in (['--version'], ['-h'], ['create'], ['context'], ['path']):\n"
        "    CliRunner().invoke(womm, args)"
    )

    assert _modules_loaded_by(code) == set()


def test_create_without_arguments_shows_its_help() -> None:
    result = CliRunner().invoke(womm, ["create"])

    assert "Usage:" in result.output
    assert "TEMPLATE" in result.output
    assert "Missing argument" not in result.output
