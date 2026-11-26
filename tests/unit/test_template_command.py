"""Tests for the template command surface."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from womm.commands.project.template import template_group


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("WOMM_HOME", str(tmp_path / "home"))
    return tmp_path


def test_list_shows_official_templates():
    result = CliRunner().invoke(template_group, ["list"])

    assert result.exit_code == 0
    assert "python" in result.output


def test_show_displays_one_template():
    result = CliRunner().invoke(template_group, ["show", "official/python"])

    assert result.exit_code == 0
    assert "python" in result.output


def test_show_unknown_template_exits_non_zero():
    result = CliRunner().invoke(template_group, ["show", "nope"])

    assert result.exit_code != 0


def test_add_registers_a_local_template(tmp_path: Path):
    source = tmp_path / "mine"
    source.mkdir()
    (source / "copier.yml").write_text("project_name:\n  type: str\n", encoding="utf-8")

    added = CliRunner().invoke(template_group, ["add", "mine", str(source)])
    listed = CliRunner().invoke(template_group, ["list"])

    assert added.exit_code == 0
    assert "mine" in listed.output


def test_add_url_exits_non_zero():
    result = CliRunner().invoke(
        template_group, ["add", "remote", "https://github.com/acme/tpl.git"]
    )

    assert result.exit_code != 0
    assert "not supported yet" in result.output


# ///////////////////////////////////////////////////////////////
# INTERACTIVE MODE (-I)
# ///////////////////////////////////////////////////////////////


def _source(tmp_path: Path, name: str = "mine") -> Path:
    source = tmp_path / name
    source.mkdir()
    (source / "copier.yml").write_text(
        '_womm:\n  description: "from wizard"\n', encoding="utf-8"
    )
    return source


def _user_ids() -> set[str]:
    from womm.services.project.template_store_service import TemplateStoreService

    return {
        e.qualified_id
        for e in TemplateStoreService().list_templates()
        if e.origin.value == "user"
    }


def _pick(monkeypatch: pytest.MonkeyPatch, answer: str) -> None:
    from womm.ui.project.templates import template_wizard

    monkeypatch.setattr(template_wizard, "prompt_choice", lambda _msg, _ids: answer)


def test_add_interactive_asks_previews_and_registers(tmp_path: Path):
    source = _source(tmp_path)

    result = CliRunner().invoke(
        template_group, ["add", "-I"], input=f"mine\n{source}\ny\n"
    )

    assert result.exit_code == 0, result.output
    assert "from wizard" in result.output
    assert _user_ids() == {"user/mine"}


def test_add_interactive_declined_registers_nothing(tmp_path: Path):
    source = _source(tmp_path)

    result = CliRunner().invoke(
        template_group, ["add", "mine", str(source), "-I"], input="n\n"
    )

    assert result.exit_code == 0, result.output
    assert _user_ids() == set()


def test_add_without_source_and_without_interactive_is_a_usage_error():
    result = CliRunner().invoke(template_group, ["add", "mine"])

    assert result.exit_code == 2
    assert "-I" in result.output


def test_remove_interactive_picks_and_confirms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    CliRunner().invoke(template_group, ["add", "mine", str(_source(tmp_path))])
    _pick(monkeypatch, "user/mine")

    result = CliRunner().invoke(template_group, ["remove", "-I"], input="y\n")

    assert result.exit_code == 0, result.output
    assert _user_ids() == set()


def test_remove_interactive_without_user_template_fails():
    result = CliRunner().invoke(template_group, ["remove", "-I"])

    assert result.exit_code == 1
    assert "No user template registered" in result.output


def test_update_interactive_asks_the_new_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    CliRunner().invoke(template_group, ["add", "mine", str(_source(tmp_path))])
    moved = _source(tmp_path, "moved")
    _pick(monkeypatch, "user/mine")

    result = CliRunner().invoke(template_group, ["update", "-I"], input=f"{moved}\ny\n")

    from womm.services.project.template_store_service import TemplateStoreService

    assert result.exit_code == 0, result.output
    assert TemplateStoreService().resolve("user/mine").copied_from == moved.resolve()


def test_init_interactive_scaffolds_then_registers(tmp_path: Path):
    destination = tmp_path / "skeleton"

    result = CliRunner().invoke(
        template_group,
        ["init", "-I", "--defaults"],
        input=f"{destination}\ny\n\n",
    )

    assert result.exit_code == 0, result.output
    assert (destination / "copier.yml").is_file()
    assert _user_ids() == {"user/skeleton"}
