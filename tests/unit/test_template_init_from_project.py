"""End-to-end tests for ``womm template init --from``."""

import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from womm.commands.project.template import template_group
from womm.interfaces.project.template_store_interface import (
    TemplateStoreInterface,
)
from womm.services.project.copier_project_creation_service import (
    CopierProjectCreationService,
    ProjectCreationRequest,
)

GIT = shutil.which("git") or "git"

SOURCE_FILES = {
    "pyproject.toml": (
        b'[project]\r\nname = "Flash-Excel"\r\nversion = "1.5.1"\r\n\r\n'
        b'[project.scripts]\r\nflash-excel = "flash_excel.cli:main"\r\n\r\n'
        b'[[tool.importlinter.contracts]]\r\ncontainers = ["flash_excel"]\r\n'
    ),
    "src/flash_excel/__init__.py": b'\xef\xbb\xbf"""flash_excel."""\n',
    "src/flash_excel/cli.py": b"def main():\n    return 'flash-excel'\n",
    ".github/workflows/ci.yml": (
        b"name: flash-excel\non: push\njobs:\n  ci:\n    runs-on: ubuntu-latest\n"
        b"    steps:\n      - run: echo ${{ github.ref }} {{ user }} {% if x %}\n"
    ),
    "page.html.jinja": b"{{ user }} flash-excel\n",
    "README.md": b"# Flash-Excel\r\n",
}


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOMM_HOME", str(tmp_path / "home"))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "flash-excel"
    root.mkdir()
    for args in (("init", "-q"), ("config", "core.autocrlf", "false")):
        subprocess.run([GIT, "-C", str(root), *args], check=True)
    for name, data in SOURCE_FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    subprocess.run([GIT, "-C", str(root), "add", "-A"], check=True)
    return root


def _extract(project: Path, destination: Path):
    return TemplateStoreInterface().init_template(
        destination,
        answers={"template_name": "webview"},
        defaults=True,
        source=project,
    )


def _render(template: Path, destination: Path, project_name: str) -> Path:
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=template,
            destination=destination,
            answers={"project_name": project_name},
            defaults=True,
        )
    )
    return destination


def test_extracted_template_renders_a_project_under_new_names(
    project: Path, tmp_path: Path
):
    template = tmp_path / "tpl"
    result = _extract(project, template)
    assert result.success is True, result.error
    assert result.extraction is not None

    for name, package in (("New-App", "new_app"), ("other.tool", "other_tool")):
        slug = package.replace("_", "-")
        out = _render(template, tmp_path / f"out-{package}", name)

        pyproject = tomllib.loads((out / "pyproject.toml").read_text("utf-8"))
        assert pyproject["project"]["name"] == name
        assert pyproject["project"]["version"] == "1.5.1"
        assert pyproject["project"]["scripts"] == {slug: f"{package}.cli:main"}
        assert pyproject["tool"]["importlinter"]["contracts"] == [
            {"containers": [package]}
        ]
        assert (out / "src" / package / "__init__.py").read_bytes() == (
            b'\xef\xbb\xbf"""' + package.encode() + b'."""\n'
        )
        workflow = (out / ".github/workflows/ci.yml").read_text("utf-8")
        assert workflow.splitlines()[-1].endswith(
            "echo ${{ github.ref }} {{ user }} {% if x %}"
        )
        assert yaml.safe_load(workflow)["name"] == slug
        assert (out / "page.html.jinja").read_bytes() == (
            b"{{ user }} " + slug.encode() + b"\n"
        )
        assert (out / "README.md").read_bytes() == b"# " + name.encode() + b"\n"


def test_template_readme_placeholder_is_left_out(project: Path, tmp_path: Path):
    template = tmp_path / "tpl"
    _extract(project, template)

    assert (template / "README.md").is_file()
    assert not (template / "template" / "README.md.jinja").exists()
    assert (template / "template" / "README.md.womm").is_file()


def test_a_refused_extraction_writes_nothing(tmp_path: Path):
    template = tmp_path / "tpl"

    result = _extract(tmp_path / "missing-root", template)

    assert result.success is False
    assert not template.exists()


def test_cli_init_from_reports_the_extraction(project: Path, tmp_path: Path):
    result = CliRunner().invoke(
        template_group,
        [
            "init",
            str(tmp_path / "tpl"),
            "--from",
            str(project),
            "--exclude",
            "page.html.jinja",
            "--defaults",
            "--data",
            "template_name=webview",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Extracted from the project" in result.output
    assert "heuristic" in result.output
    assert not (tmp_path / "tpl" / "template" / "page.html.jinja.womm").exists()


def test_cli_exclude_needs_from(tmp_path: Path):
    result = CliRunner().invoke(
        template_group, ["init", str(tmp_path / "tpl"), "--exclude", "x"]
    )

    assert result.exit_code == 2
    assert "--exclude needs --from" in result.output


def test_extraction_flags_cannot_be_set_without_from(tmp_path: Path):
    template = tmp_path / "tpl"

    result = TemplateStoreInterface().init_template(
        template,
        answers={"template_name": "plain", "extracted": "true"},
        defaults=True,
    )

    assert result.success is True
    assert "_envops" not in (template / "copier.yml").read_text("utf-8")
    assert (template / "template" / "README.md.jinja").is_file()
