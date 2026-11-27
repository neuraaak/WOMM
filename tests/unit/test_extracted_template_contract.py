"""Copier contract that templates extracted from a project rely on.

An extracted template keeps the project's files as they are: GitHub
expressions, Jinja sources and TOML arrays of tables must survive rendering.
It does so with dedicated delimiters (``_envops``) and a dedicated suffix
(``_templates_suffix``); this test pins both on the installed Copier.
"""

from pathlib import Path

from womm.services.project.copier_project_creation_service import (
    CopierProjectCreationService,
    ProjectCreationRequest,
)

COPIER_YML = """\
_subdirectory: template
_templates_suffix: ".womm"
_envops:
  block_start_string: "[%@"
  block_end_string: "@%]"
  variable_start_string: "[[@"
  variable_end_string: "@]]"
  comment_start_string: "[#@"
  comment_end_string: "@#]"

project_name:
  type: str
  default: "my-project"

project_slug:
  type: str
  default: "[[@ project_name | lower @]]"
  when: false

package_name:
  type: str
  default: "[[@ project_slug | replace('-', '_') @]]"
"""


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_dedicated_delimiters_and_suffix_keep_project_files_verbatim(tmp_path: Path):
    template = tmp_path / "tpl"
    root = template / "template"
    _write(template / "copier.yml", COPIER_YML.encode())
    _write(
        root / "pyproject.toml.womm",
        b'[project]\r\nname = "[[@ project_slug @]]"\r\n\r\n'
        b'[[tool.importlinter.contracts]]\r\nname = "x"\r\n',
    )
    workflow = b"run: echo ${{ github.ref }} {% raw %}\n"
    jinja_source = b"Hello {{ user }} {% if x %}y{% endif %}\n"
    _write(root / ".github" / "workflows" / "ci.yml", workflow)
    _write(root / "macro.html.jinja", jinja_source)
    _write(root / "src" / "[[@ package_name @]]" / "__init__.py", b"")
    _write(
        root / "src" / "[[@ package_name @]]" / "core.py.womm",
        b"import [[@ package_name @]].x\n",
    )

    out = tmp_path / "out"
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=template,
            destination=out,
            answers={"project_name": "New-App"},
            defaults=True,
        )
    )

    # Jinja renders line endings as LF: a rendered file loses its CRLF.
    assert (out / "pyproject.toml").read_bytes() == (
        b'[project]\nname = "new-app"\n\n[[tool.importlinter.contracts]]\nname = "x"\n'
    )
    assert (out / ".github" / "workflows" / "ci.yml").read_bytes() == workflow
    assert (out / "macro.html.jinja").read_bytes() == jinja_source
    assert (out / "src" / "new_app" / "__init__.py").is_file()
    assert (out / "src" / "new_app" / "core.py").read_bytes() == b"import new_app.x\n"
