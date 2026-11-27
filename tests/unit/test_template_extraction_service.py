"""Tests for the extraction of a Copier template from a git project."""

import hashlib
import shutil
import subprocess
from pathlib import Path, PurePosixPath

import pytest

from womm.exceptions.project import ProjectServiceError
from womm.services.project.template_extraction_service import (
    TemplateExtractionService,
)
from womm.services.project.template_extraction_trace import (
    TRACE_FILENAME,
    read_trace,
)

PYPROJECT = b"""\
[project]
name = "Flash-Excel"
version = "1.5.1"
dependencies = ["flash-excel-extra>=1", "requests"]

[project.scripts]
flash-excel = "flash_excel.cli:main"

[[tool.importlinter.contracts]]
containers = ["flash_excel"]
"""


GIT = shutil.which("git") or "git"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        [GIT, "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _repo(root: Path, files: dict[str, bytes]) -> Path:
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "core.autocrlf", "false")
    for name, data in files.items():
        _write(root / name, data)
    _git(root, "add", "-A")
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return _repo(
        tmp_path / "flash-excel",
        {
            "pyproject.toml": PYPROJECT,
            "src/flash_excel/__init__.py": b'\xef\xbb\xbf"""flash_excel."""\r\n',
            "src/flash_excel/core.py": (
                b"import flash_excel.x\notherflash_excel = 1\nFLASH_EXCEL = 2\n"
            ),
            ".github/workflows/ci.yml": b"name: flash-excel ${{ github.ref }}\n",
            "macro.html.jinja": b"{{ user }} {% if x %}flash-excel{% endif %}\n",
            "untouched.txt": b"no name here {{ x }}\r\n",
            "logo.bin": b"\x00flash_excel\x00",
            ".env": b"TOKEN=secret\n",
            ".env.example": b"TOKEN=\n",
            "tests/test_credentials.py": b"",
            ".tufup-repo-config": b"{}",
            "docs/index.md": b"flash-excel\n",
            "uv.lock": b'name = "flash-excel"\n',
            ".womm/copier.yml": b"old\n",
        },
    )


def _plan(source: Path, destination: Path, excludes: tuple[str, ...] = ()):
    return TemplateExtractionService().plan(source, destination, excludes)


# ///////////////////////////////////////////////////////////////
# IDENTITY AND CONTENT
# ///////////////////////////////////////////////////////////////


def test_names_become_variables_and_everything_else_is_kept(
    project: Path, tmp_path: Path
):
    plan = _plan(project, tmp_path / "tpl")
    TemplateExtractionService().write(plan)
    out = tmp_path / "tpl" / "template"

    report = plan.report
    assert report.variables == {
        "project_name": "Flash-Excel",
        "project_slug": "flash-excel",
        "package_name": "flash_excel",
    }
    assert (out / "pyproject.toml.womm").read_bytes() == (
        PYPROJECT.replace(b'"Flash-Excel"', b'"[[@ project_name @]]"')
        .replace(b"flash-excel =", b"[[@ project_slug @]] =")
        .replace(b'"flash_excel.cli', b'"[[@ package_name @]].cli')
        .replace(b'["flash_excel"]', b'["[[@ package_name @]]"]')
    )
    # The bounded replacement leaves names that only contain the project's.
    assert b"flash-excel-extra" in (out / "pyproject.toml.womm").read_bytes()
    package = out / "src" / "[[@ package_name @]]"
    assert (package / "__init__.py.womm").read_bytes() == (
        b'\xef\xbb\xbf"""[[@ package_name @]]."""\r\n'
    )
    assert (package / "core.py.womm").read_bytes() == (
        b"import [[@ package_name @]].x\notherflash_excel = 1\nFLASH_EXCEL = 2\n"
    )
    assert "src/flash_excel/core.py:2" in report.residuals
    assert "src/flash_excel/core.py:3" in report.residuals
    assert (out / ".github/workflows/ci.yml.womm").read_bytes() == (
        b"name: [[@ project_slug @]] ${{ github.ref }}\n"
    )
    assert (out / "macro.html.jinja.womm").read_bytes() == (
        b"{{ user }} {% if x %}[[@ project_slug @]]{% endif %}\n"
    )
    assert (out / "untouched.txt").read_bytes() == b"no name here {{ x }}\r\n"
    assert (out / "logo.bin").read_bytes() == b"\x00flash_excel\x00"
    assert (out / ".env.example").is_file()
    assert any("LF line endings" in w for w in report.warnings)
    assert any("Lockfiles" in w for w in report.warnings)


def test_risky_and_internal_files_are_excluded(project: Path, tmp_path: Path):
    plan = _plan(project, tmp_path / "tpl")
    TemplateExtractionService().write(plan)
    out = tmp_path / "tpl" / "template"

    excluded = dict(plan.report.excluded)
    assert excluded[".env"] == "file at risk of holding secrets"
    assert excluded[".tufup-repo-config"] == "file at risk of holding secrets"
    assert excluded["tests/test_credentials.py"] == "file at risk of holding secrets"
    assert excluded[".womm/copier.yml"] == "WOMM or git internal"
    assert not (out / ".env").exists()
    assert not (out / ".womm").exists()


def test_user_excludes_and_unmatched_patterns_are_reported(
    project: Path, tmp_path: Path
):
    plan = _plan(project, tmp_path / "tpl", ("docs/", "nothing/*"))

    assert dict(plan.report.excluded)["docs/index.md"] == "--exclude docs/"
    assert "--exclude nothing/* matched no tracked file" in plan.report.warnings


def test_a_destination_inside_the_project_is_never_ingested(project: Path):
    destination = project / "templates" / "mine"
    _write(destination / "copier.yml", b"x\n")
    _git(project, "add", "-A")

    plan = _plan(project, destination)

    assert dict(plan.report.excluded)["templates/mine/copier.yml"] == (
        "inside the template destination"
    )


def test_equal_variants_take_the_most_constrained_variable(tmp_path: Path):
    source = _repo(
        tmp_path / "foo",
        {
            "pyproject.toml": b'[project]\nname = "foo"\n',
            "src/foo/__init__.py": b"",
        },
    )

    plan = _plan(source, tmp_path / "tpl")

    assert plan.report.variables == {"package_name": "foo"}
    assert any("not project_name" in w for w in plan.report.warnings)
    assert plan.meta_answers == {"has_identity": "true", "has_package": "true"}


def test_a_project_without_name_is_copied_verbatim(tmp_path: Path):
    source = _repo(tmp_path / "plain", {"a.txt": b"plain\n"})

    plan = _plan(source, tmp_path / "tpl")

    assert plan.report.variables == {}
    assert plan.report.copied == ["a.txt"]
    assert plan.meta_answers == {"has_identity": "false", "has_package": "false"}


# ///////////////////////////////////////////////////////////////
# REFUSALS
# ///////////////////////////////////////////////////////////////


def test_a_delimiter_in_a_rendered_file_is_refused(tmp_path: Path):
    source = _repo(
        tmp_path / "foo",
        {
            "pyproject.toml": b'[project]\nname = "foo-app"\n',
            "a.txt": b"foo-app [[@ x @]]\n",
        },
    )

    with pytest.raises(ProjectServiceError, match="a.txt contains a template"):
        _plan(source, tmp_path / "tpl")


def test_a_delimiter_in_a_copied_file_is_harmless(tmp_path: Path):
    source = _repo(
        tmp_path / "foo",
        {"pyproject.toml": b'[project]\nname = "foo-app"\n', "a.txt": b"[[@ x @]]\n"},
    )

    assert "a.txt" in _plan(source, tmp_path / "tpl").report.copied


def test_a_tracked_template_suffix_is_refused(tmp_path: Path):
    source = _repo(tmp_path / "foo", {"conf.womm/a.txt": b""})

    with pytest.raises(ProjectServiceError, match="template suffix"):
        _plan(source, tmp_path / "tpl")


@pytest.mark.parametrize("relation", ["same", "parent"])
def test_a_destination_over_the_project_is_refused(tmp_path: Path, relation: str):
    source = _repo(tmp_path / "foo", {"a.txt": b""})
    destination = source if relation == "same" else tmp_path

    with pytest.raises(ProjectServiceError, match="cannot be the project"):
        _plan(source, destination)


def test_a_subdirectory_of_a_repository_is_refused(tmp_path: Path):
    source = _repo(tmp_path / "foo", {"sub/a.txt": b""})

    with pytest.raises(ProjectServiceError, match="root of a git repository"):
        _plan(source / "sub", tmp_path / "tpl")


def test_a_directory_outside_git_is_refused_with_gits_message(tmp_path: Path):
    source = tmp_path / "plain"
    source.mkdir()

    with pytest.raises(ProjectServiceError) as caught:
        _plan(source, tmp_path / "tpl")

    assert "git rev-parse failed" in str(caught.value)
    assert "not a git repository" in str(caught.value).lower()


def test_unmerged_files_are_refused(tmp_path: Path):
    source = _repo(tmp_path / "foo", {"a.txt": b"a\n"})
    blob = _git(source, "hash-object", "-w", "a.txt").strip()
    _git(source, "rm", "-q", "--cached", "a.txt")
    subprocess.run(
        [GIT, "-C", str(source), "update-index", "--index-info"],
        # Bytes: text mode would send CRLF on Windows and git would skip "a.txt\r".
        input=f"100644 {blob} 1\ta.txt\n100644 {blob} 2\ta.txt\n".encode(),
        check=True,
    )

    with pytest.raises(ProjectServiceError, match="unmerged"):
        _plan(source, tmp_path / "tpl")


def test_submodules_are_left_out(tmp_path: Path):
    source = _repo(tmp_path / "foo", {"a.txt": b""})
    _git(
        source,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{'1' * 40},vendor/lib",
    )

    plan = _plan(source, tmp_path / "tpl")

    assert dict(plan.report.excluded)["vendor/lib"] == "git submodule"


def test_symbolic_links_are_left_out(tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    source = _repo(tmp_path / "foo", {"a.txt": b""})
    try:
        (source / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links need a privilege on this machine")
    _git(source, "add", "link.txt")

    plan = _plan(source, tmp_path / "tpl")

    assert "link.txt" in dict(plan.report.excluded)


@pytest.mark.parametrize(
    "files",
    [
        ("Flash.Excel.txt", "flash-excel.txt"),
        ("Flash.Excel", "flash-excel/a.txt"),
    ],
)
def test_paths_that_render_alike_are_refused(tmp_path: Path, files: tuple[str, ...]):
    # project_name=app renders project_name and project_slug alike.
    source = _repo(
        tmp_path / "foo",
        {"pyproject.toml": b'[project]\nname = "Flash.Excel"\n'}
        | dict.fromkeys(files, b"x\n"),
    )

    with pytest.raises(ProjectServiceError, match="can render to the same path"):
        _plan(source, tmp_path / "tpl")


def test_an_excluded_manifest_is_never_read(tmp_path: Path):
    source = _repo(
        tmp_path / "foo",
        {"pyproject.toml": b"not = [valid toml", "a.txt": b"a\n"},
    )

    plan = _plan(source, tmp_path / "tpl", ("pyproject.toml",))

    assert plan.report.copied == ["a.txt"]


def test_the_trace_records_provenance_and_baseline(project: Path, tmp_path: Path):
    destination = tmp_path / "tpl"
    plan = _plan(project, destination, ("docs/",))
    TemplateExtractionService().write(plan)

    trace = read_trace(destination)

    assert trace is not None
    assert trace.origin == "../flash-excel"
    assert trace.excludes == ["docs/"]
    assert trace.variables["package_name"] == "flash_excel"
    assert trace.contract["suffix"] == ".womm"
    item = trace.files[PurePosixPath("src/flash_excel/core.py")]
    assert item.target == PurePosixPath("src/[[@ package_name @]]/core.py.womm")
    written = destination / "template" / item.target
    assert item.sha256 == hashlib.sha256(written.read_bytes()).hexdigest()
    assert PurePosixPath("docs/index.md") not in trace.files


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        '{"schema_version": 2}',
        '{"schema_version": 1, "from": "..", "excludes": [], "variables": {},'
        ' "contract": {}, "files": {"../x": {"target": "x", "sha256": "'
        + "a" * 64
        + '"}}}',
        '{"schema_version": 1, "from": "..", "excludes": [], "variables": {},'
        ' "contract": {}, "files": {"x": {"target": "C:/x", "sha256": "'
        + "a" * 64
        + '"}}}',
        '{"schema_version": 1, "from": "..", "excludes": [], "variables": {},'
        ' "contract": {}, "files": {"x": {"target": "x", "sha256": "nothex"}}}',
        '{"schema_version": true, "from": "..", "excludes": [], "variables": {},'
        ' "contract": {}, "files": {}}',
        '{"schema_version": 1, "from": "C:/elsewhere", "excludes": [],'
        ' "variables": {}, "contract": {}, "files": {}}',
        '{"schema_version": 1, "from": "/elsewhere", "excludes": [],'
        ' "variables": {}, "contract": {}, "files": {}}',
        '{"schema_version": 1, "from": "..", "excludes": [], "variables": {},'
        ' "contract": {}, "files": {"a": {"target": "X", "sha256": "HASH"},'
        ' "b": {"target": "x", "sha256": "HASH"}}}',
        '{"schema_version": 1, "from": "..", "excludes": [], "variables": {},'
        ' "contract": {}, "files": {"a": {"target": "d", "sha256": "HASH"},'
        ' "b": {"target": "d/e", "sha256": "HASH"}}}',
    ],
)
def test_an_invalid_trace_is_an_error(tmp_path: Path, payload: str):
    payload = payload.replace("HASH", "a" * 64)
    (tmp_path / TRACE_FILENAME).write_text(payload, encoding="utf-8")

    with pytest.raises(ProjectServiceError, match="trace is invalid"):
        read_trace(tmp_path)


def test_no_trace_is_none(tmp_path: Path):
    assert read_trace(tmp_path) is None
