"""Tool choices must agree across dependencies, configuration and execution."""

import json
import os
import secrets
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

from womm._version import __version__
from womm.exceptions.project import ProjectServiceError
from womm.services.project.copier_project_creation_service import (
    CopierProjectCreationService,
    ProjectCreationRequest,
)
from womm.services.project.template_store_service import TemplateStoreService

JS_PROFILES = [
    ("none", "biome"),
    ("none", "eslint-prettier"),
    ("react", "biome"),
    ("react", "eslint-prettier"),
    ("vue", "eslint-prettier"),
]


def render(destination: Path, language: str, **answers: object) -> Path:
    """Render with the same service and provenance as the CLI."""
    source = TemplateStoreService().resolve(f"official/{language}").source
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=source,
            destination=destination,
            answers={"project_name": "acme", **answers},
            defaults=True,
        )
    )
    return destination


@pytest.mark.parametrize("tooling", ["ruff", "black-isort"])
@pytest.mark.parametrize("type_checker", ["ty", "mypy", "pyright"])
@pytest.mark.parametrize("use_uv", [False, True])
def test_python_choices_reach_every_consumer(
    tmp_path: Path, tooling: str, type_checker: str, use_uv: bool
):
    out = render(
        tmp_path / "project",
        "python",
        tooling=tooling,
        type_checker=type_checker,
        use_uv=use_uv,
        use_src_layout=use_uv,
        with_coverage=False,
    )
    config = tomllib.loads((out / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = {
        requirement.name: requirement
        for requirement in map(Requirement, config["dependency-groups"]["dev"])
    }
    assert requirements["ruff"].specifier == SpecifierSet(
        config["tool"]["ruff"]["required-version"]
    )
    for requirement in requirements.values():
        constraint = str(requirement.specifier)
        assert constraint.startswith("~=")
        major, minor, patch = map(int, constraint.removeprefix("~=").split("."))
        assert f"{major}.{minor}.{patch}" in requirement.specifier
        assert f"{major}.{minor}.{patch + 1}" in requirement.specifier
        assert f"{major}.{minor + 1}.0" not in requirement.specifier
        if patch:
            assert f"{major}.{minor}.{patch - 1}" not in requirement.specifier
    assert {"ty", "mypy", "pyright"} & requirements.keys() == {type_checker}
    assert "pytest-cov" not in requirements
    assert "coverage" not in config["tool"]
    assert ("I" in config["tool"]["ruff"]["lint"]["select"]) is (tooling == "ruff")
    assert ("black" in requirements) is (tooling == "black-isort")
    if tooling == "black-isort":
        assert "required-version" not in config["tool"]["black"]
        assert config["tool"]["isort"]["profile"] == "black"
        assert "format" not in config["tool"]["ruff"]
    settings = json.loads((out / ".vscode/settings.json").read_text(encoding="utf-8"))
    extensions = json.loads(
        (out / ".vscode/extensions.json").read_text(encoding="utf-8")
    )["recommendations"]
    assert {
        "ty": "astral-sh.ty",
        "mypy": "ms-python.mypy-type-checker",
        "pyright": "ms-python.vscode-pylance",
    }[type_checker] in extensions
    assert settings["ruff.importStrategy"] == "fromEnvironment"
    assert settings["[python]"]["editor.defaultFormatter"] == (
        "charliermarsh.ruff" if tooling == "ruff" else "ms-python.black-formatter"
    )
    hooks = yaml.safe_load(
        (out / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )["repos"][0]["hooks"]
    assert {"ty", "mypy", "pyright"} & {hook["id"] for hook in hooks} == {type_checker}
    workflow = yaml.safe_load((out / ".github/workflows/ci.yml").read_text("utf-8"))
    commands = {
        step.get("name"): step.get("run") for step in workflow["jobs"]["test"]["steps"]
    }
    assert type_checker in commands["Type check"]
    assert ("ruff format" in commands["Format check"]) is (tooling == "ruff")
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert commands["Type check"].replace(" --no-sync", "") in readme


@pytest.mark.parametrize("framework,tooling", JS_PROFILES)
@pytest.mark.parametrize("typescript", [False, True])
def test_javascript_choices_reach_every_consumer(
    tmp_path: Path, framework: str, tooling: str, typescript: bool
):
    out = render(
        tmp_path / "project",
        "javascript",
        framework=framework,
        tooling=tooling,
        typescript=typescript,
        with_knip=True,
        with_coverage=True,
    )
    package = json.loads((out / "package.json").read_text(encoding="utf-8"))
    deps = package["devDependencies"]
    assert all(
        value.startswith("~")
        for name, value in deps.items()
        if not name.startswith("@types/")
        and name not in ("vitest", "@vitest/coverage-v8")
    )
    assert ("@biomejs/biome" in deps) is (tooling == "biome")
    assert (out / "biome.json").exists() is (tooling == "biome")
    assert (out / "eslint.config.mjs").exists() is (tooling == "eslint-prettier")
    if tooling == "biome":
        schema = json.loads((out / "biome.json").read_text(encoding="utf-8"))["$schema"]
        assert schema == "./node_modules/@biomejs/biome/configuration_schema.json"
    assert deps["vitest"] == deps["@vitest/coverage-v8"]
    assert package["scripts"]["test:coverage"] == "vitest run --coverage"
    assert "knip" in deps
    assert (
        f"@{deps['knip'].removeprefix('~')}/"
        in json.loads((out / "knip.json").read_text(encoding="utf-8"))["$schema"]
    )
    workflow = yaml.safe_load((out / ".github/workflows/ci.yml").read_text("utf-8"))
    commands = {
        step.get("name"): step.get("run")
        for step in workflow["jobs"]["quality"]["steps"]
    }
    assert commands["Test"].endswith("test:coverage")
    assert any(
        command and command.endswith("check:unused") for command in commands.values()
    )
    settings = json.loads((out / ".vscode/settings.json").read_text(encoding="utf-8"))
    assert settings["editor.defaultFormatter"] == (
        "biomejs.biome" if tooling == "biome" else "esbenp.prettier-vscode"
    )


@pytest.mark.parametrize("language", ["python", "javascript"])
def test_provenance_records_effective_choices_without_local_paths(
    tmp_path: Path, language: str
):
    out = render(tmp_path / "project", language, _womm_version="not-the-generator")
    record = json.loads((out / ".womm-template.json").read_text(encoding="utf-8"))
    assert record["womm_version"] == __version__
    entry = TemplateStoreService().resolve(f"official/{language}")
    assert record["template"] == entry.qualified_id
    assert record["template_version"] == entry.version
    assert record["choices"]["tooling"] == ("ruff" if language == "python" else "biome")
    assert record["choices"]["project_name"] == "acme"
    assert "tool_versions" not in record["choices"]
    assert all(not key.startswith("_") for key in record["choices"])


@pytest.mark.parametrize("language", ["python", "javascript"])
def test_disabling_tests_omits_coverage_even_with_an_explicit_request(
    tmp_path: Path, language: str
):
    out = render(tmp_path / "project", language, with_tests=False, with_coverage=True)
    if language == "python":
        config = tomllib.loads((out / "pyproject.toml").read_text(encoding="utf-8"))
        assert "coverage" not in config["tool"]
        assert not any("pytest" in dep for dep in config["dependency-groups"]["dev"])
    else:
        package = json.loads((out / "package.json").read_text(encoding="utf-8"))
        assert "@vitest/coverage-v8" not in package["devDependencies"]
        assert "test:coverage" not in package["scripts"]


def test_vue_refuses_an_unsupported_toolchain(tmp_path: Path):
    with pytest.raises(ProjectServiceError):
        render(tmp_path / "project", "javascript", framework="vue", tooling="biome")


@pytest.mark.parametrize("manager", ["npm", "pnpm", "yarn", "bun"])
def test_biome_schema_follows_the_package_layout(tmp_path: Path, manager: str):
    out = render(tmp_path / "project", "javascript", package_manager=manager)
    config = json.loads((out / "biome.json").read_text(encoding="utf-8"))
    if manager == "yarn":
        assert "$schema" not in config
    else:
        assert config["$schema"] == (
            "./node_modules/@biomejs/biome/configuration_schema.json"
        )


def test_vitest_allows_patches_without_a_coupled_coverage_provider(tmp_path: Path):
    out = render(tmp_path / "project", "javascript", with_coverage=False)
    package = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert package["devDependencies"]["vitest"].startswith("~")
    assert "@vitest/coverage-v8" not in package["devDependencies"]


def run(command: list[str], project: Path) -> None:
    """Execute a real generated-project check, isolated from WOMM's venv."""
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    # These projects have just been rendered and intentionally have no lockfile.
    env["YARN_ENABLE_IMMUTABLE_INSTALLS"] = "false"
    env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(50)
    result = subprocess.run(
        command,
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, f"{command}:\n{result.stdout}\n{result.stderr}"


@pytest.mark.slow
@pytest.mark.parametrize("manager", ["npm", "yarn"])
def test_biome_patch_range_executes_with_its_package_layout(
    tmp_path: Path, manager: str
):
    executable = shutil.which("corepack" if manager == "yarn" else "npm")
    if executable is None:
        pytest.skip(f"{'Corepack' if manager == 'yarn' else 'npm'} is not installed")
    prefix = [executable, "yarn"] if manager == "yarn" else [executable]
    out = render(
        tmp_path / "project", "javascript", package_manager=manager, with_tests=False
    )
    run([*prefix, "install"], out)
    if manager == "yarn":
        assert (out / ".pnp.cjs").is_file()
    else:
        config = json.loads((out / "biome.json").read_text(encoding="utf-8"))
        assert (out / config["$schema"]).is_file()
    run([*prefix, "run", "format:check"], out)
    run([*prefix, "run", "lint"], out)


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
@pytest.mark.parametrize("tooling", ["ruff", "black-isort"])
@pytest.mark.parametrize("type_checker", ["ty", "mypy", "pyright"])
@pytest.mark.parametrize("framework", ["none", "django"])
def test_python_toolchain_executes(
    tmp_path: Path, tooling: str, type_checker: str, framework: str
):
    out = render(
        tmp_path / "project",
        "python",
        tooling=tooling,
        type_checker=type_checker,
        framework=framework,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        use_src_layout=tooling == "ruff",
    )
    uv = shutil.which("uv")
    assert uv is not None
    run([uv, "sync", "--group", "dev"], out)
    run([uv, "sync", "--locked", "--group", "dev"], out)
    prefix = [uv, "run", "--no-sync"]
    run([*prefix, "ruff", "check", "."], out)
    if tooling == "ruff":
        run([*prefix, "ruff", "format", "--check", "."], out)
    else:
        run([*prefix, "isort", "--check-only", "."], out)
        run([*prefix, "black", "--check", "."], out)
    run([*prefix, type_checker, *(["check", "."] if type_checker == "ty" else [])], out)
    run([*prefix, "pytest"], out)
    if framework == "django":
        run([*prefix, "python", "manage.py", "check"], out)
    run([uv, "build"], out)


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("npm") is None, reason="npm is not installed")
@pytest.mark.parametrize("framework,tooling", JS_PROFILES)
@pytest.mark.parametrize("typescript", [False, True])
def test_javascript_toolchain_executes(
    tmp_path: Path, framework: str, tooling: str, typescript: bool
):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    if int(version.removeprefix("v").split(".")[0]) < 24:
        pytest.skip("The JavaScript template requires Node.js 24 or newer")
    out = render(
        tmp_path / "project",
        "javascript",
        framework=framework,
        tooling=tooling,
        typescript=typescript,
        with_knip=True,
        with_coverage=True,
    )
    npm = shutil.which("npm")
    assert npm is not None
    run([npm, "install", "--no-audit", "--no-fund"], out)
    run([npm, "ci", "--no-audit", "--no-fund"], out)
    for script in (
        "format:check",
        "lint",
        "check:unused",
        "type-check",
        "test:coverage",
        "build",
    ):
        if script != "type-check" or typescript:
            run([npm, "run", script], out)
