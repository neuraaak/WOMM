"""Generation matrix for the official JavaScript template."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from womm.services.project.copier_project_creation_service import (
    CopierProjectCreationService,
    ProjectCreationRequest,
)
from womm.services.project.template_store_service import TemplateStoreService

# Quotes and backslashes are legal in a free-text answer and must survive
# rendering into JSON.
HOSTILE_DESCRIPTION = 'He said "hi" and a \\ backslash'

BASE_ANSWERS = {
    "project_name": "acme-app",
    "description": "A demo app",
    "author_name": "Tester",
}


def render(destination: Path, **overrides: object) -> Path:
    """Render the official JavaScript template with merged answers."""
    source = TemplateStoreService().resolve("official/javascript").source
    return render_from_source(destination, source, **overrides)


def render_from_source(destination: Path, source: Path, **overrides: object) -> Path:
    """Render a JavaScript template source with merged answers."""
    CopierProjectCreationService().create(
        ProjectCreationRequest(
            template_source=source,
            destination=destination,
            answers={**BASE_ANSWERS, **overrides},
            defaults=True,
        )
    )
    return destination


def test_standard_copier_exclusions_are_preserved(tmp_path: Path):
    source = TemplateStoreService().resolve("official/javascript").source
    copied_source = tmp_path / "template-source"
    shutil.copytree(source, copied_source)
    template = copied_source / "template"
    (template / ".DS_Store").write_text("metadata", encoding="utf-8")
    (template / "scratch.pyc").write_bytes(b"bytecode")
    (template / "~backup").write_text("backup", encoding="utf-8")
    cache = template / "__pycache__"
    cache.mkdir()
    (cache / "cached.pyc").write_bytes(b"bytecode")

    out = render_from_source(tmp_path / "rendered", copied_source)

    assert not (out / ".DS_Store").exists()
    assert not (out / "scratch.pyc").exists()
    assert not (out / "~backup").exists()
    assert not (out / "__pycache__").exists()


def test_defaults_produce_a_coherent_project(tmp_path: Path):
    out = render(tmp_path / "p")

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "acme-app"
    assert manifest["type"] == "module"
    assert (out / ".nvmrc").read_text(encoding="utf-8").strip() == "24"
    assert "vitest" in manifest["devDependencies"]
    assert "@biomejs/biome" in manifest["devDependencies"]
    assert (out / "biome.json").is_file()
    assert (out / ".vscode" / "settings.json").is_file()
    assert not (out / ".eslintrc.json").exists()
    assert not (out / "eslint.config.mjs").exists()
    assert not (out / "prettier.config.mjs").exists()
    assert not (out / ".prettierignore").exists()
    assert not (out / "index.html").exists()
    assert not (out / "vite.config.mjs").exists()
    assert not (out / "tsconfig.json").exists()


def test_typescript_adds_a_tsconfig(tmp_path: Path):
    out = render(tmp_path / "p", typescript=True)

    json.loads((out / "tsconfig.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("framework", ["none", "react", "vue"])
@pytest.mark.parametrize("typescript", [False, True])
def test_every_framework_renders_in_both_language_modes(
    tmp_path: Path, framework: str, typescript: bool
):
    out = render(
        tmp_path / f"{framework}-{typescript}",
        framework=framework,
        typescript=typescript,
    )

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "acme-app"
    assert (out / "tsconfig.json").is_file() is typescript
    assert (out / "index.html").is_file() is (framework != "none")
    assert (out / "vite.config.mjs").is_file() is (framework != "none")


@pytest.mark.parametrize("manager", ["npm", "pnpm", "yarn", "bun"])
def test_each_package_manager_renders(tmp_path: Path, manager: str):
    out = render(tmp_path / manager, package_manager=manager)

    assert (out / "package.json").is_file()


@pytest.mark.parametrize("license_id", ["MIT", "Apache-2.0", "proprietary"])
def test_license_metadata_matches_selected_terms(tmp_path: Path, license_id: str):
    out = render(tmp_path / license_id, license=license_id)

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert manifest["license"] == (
        "UNLICENSED" if license_id == "proprietary" else license_id
    )


def test_bun_readme_uses_explicit_run_for_the_test_script(tmp_path: Path):
    out = render(tmp_path / "p", package_manager="bun")

    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "bun run test" in readme
    assert "bun test\n" not in readme


def test_tests_can_be_disabled(tmp_path: Path):
    out = render(tmp_path / "p", with_tests=False)

    assert not (out / "tests").exists()


def test_vscode_files_can_be_disabled(tmp_path: Path):
    out = render(tmp_path / "p", with_vscode=False)

    assert not (out / ".vscode").exists()
    assert ".vscode/" in (out / ".gitignore").read_text(encoding="utf-8")


def test_ci_is_generated_by_default_and_is_valid_yaml(tmp_path: Path):
    out = render(tmp_path / "p")

    workflow = out / ".github" / "workflows" / "ci.yml"
    assert workflow.is_file()
    assert yaml.compose(workflow.read_text(encoding="utf-8")) is not None


def test_ci_can_be_disabled(tmp_path: Path):
    out = render(tmp_path / "p", with_ci=False)

    assert not (out / ".github").exists()


@pytest.mark.parametrize(
    ("manager", "setup_action", "lockfile", "strict_install"),
    [
        (
            "npm",
            "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1",
            "package-lock.json",
            "npm ci",
        ),
        (
            "pnpm",
            "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1",
            "pnpm-lock.yaml",
            "pnpm install --frozen-lockfile",
        ),
        (
            "yarn",
            "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1",
            "yarn.lock",
            "yarn install --immutable",
        ),
        (
            "bun",
            "oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6",
            "bun.lock",
            "bun install --frozen-lockfile",
        ),
    ],
)
def test_ci_installs_with_the_selected_package_manager(
    tmp_path: Path,
    manager: str,
    setup_action: str,
    lockfile: str,
    strict_install: str,
):
    out = render(tmp_path / manager, package_manager=manager)
    workflow = yaml.safe_load(
        (out / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["quality"]["steps"]

    assert any(step.get("uses") == setup_action for step in steps)
    install = next(
        step["run"] for step in steps if step.get("name") == "Install dependencies"
    )
    assert install == strict_install
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert lockfile in readme
    assert "CI installs only from that lockfile" in readme
    assert workflow["permissions"] == {"contents": "read"}
    assert any(
        step.get("uses") == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        for step in steps
    )
    if manager in {"pnpm", "yarn"}:
        corepack = next(
            step["run"] for step in steps if step.get("name") == "Enable Corepack"
        )
        assert "corepack@0.36.0" in corepack
        assert "corepack enable" in corepack
    if manager != "bun":
        assert workflow["jobs"]["quality"]["strategy"]["matrix"]["node-version"] == [
            24,
            26,
        ]
    else:
        assert "strategy" not in workflow["jobs"]["quality"]
        assert not (out / ".nvmrc").exists()


@pytest.mark.parametrize(
    ("manager", "run_prefix"),
    [
        ("npm", "npm run"),
        ("pnpm", "pnpm"),
        ("yarn", "yarn"),
        ("bun", "bun run"),
    ],
)
@pytest.mark.parametrize("typescript", [False, True])
@pytest.mark.parametrize("with_tests", [False, True])
def test_ci_runs_only_generated_quality_scripts(
    tmp_path: Path,
    manager: str,
    run_prefix: str,
    typescript: bool,
    with_tests: bool,
):
    out = render(
        tmp_path / f"{manager}-{typescript}-{with_tests}",
        package_manager=manager,
        typescript=typescript,
        with_tests=with_tests,
    )
    workflow = yaml.safe_load(
        (out / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["quality"]["steps"]
    commands = {
        step["name"]: step["run"] for step in steps if "name" in step and "run" in step
    }

    assert commands["Format check"] == f"{run_prefix} format:check"
    assert commands["Lint"] == f"{run_prefix} lint"
    assert commands["Build"] == f"{run_prefix} build"
    assert ("Type check" in commands) is typescript
    assert ("Test" in commands) is with_tests
    if typescript:
        assert commands["Type check"] == f"{run_prefix} type-check"
    if with_tests:
        assert commands["Test"] == f"{run_prefix} test"


@pytest.mark.parametrize("description", ["A demo app", HOSTILE_DESCRIPTION])
def test_rendered_package_json_is_valid_json(tmp_path: Path, description: str):
    out = render(
        tmp_path / "p", framework="react", typescript=True, description=description
    )

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert manifest["description"] == description


def test_react_uses_vite_instead_of_react_scripts(tmp_path: Path):
    out = render(tmp_path / "p", framework="react")

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert "vite" in manifest["devDependencies"]
    assert "@vitejs/plugin-react" in manifest["devDependencies"]
    assert "react-scripts" not in manifest["devDependencies"]


def test_vue_uses_vite_instead_of_vue_cli(tmp_path: Path):
    out = render(tmp_path / "p", framework="vue")

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert "vite" in manifest["devDependencies"]
    assert "@vitejs/plugin-vue" in manifest["devDependencies"]
    assert "@vue/cli-service" not in manifest["devDependencies"]


def test_vscode_settings_are_modernized(tmp_path: Path):
    out = render(tmp_path / "p")

    settings = json.loads(
        (out / ".vscode" / "settings.json").read_text(encoding="utf-8")
    )
    assert "eslint.useFlatConfig" not in settings
    assert settings["editor.rulers"] == [100]
    assert settings["search.exclude"]["**/node_modules"] is True
    assert settings["search.exclude"]["**/dist"] is True
    assert settings["search.exclude"]["**/coverage"] is True


def test_vscode_recommends_vitest_extension_when_tests_enabled(tmp_path: Path):
    out = render(tmp_path / "p", with_tests=True)

    extensions = json.loads(
        (out / ".vscode" / "extensions.json").read_text(encoding="utf-8")
    )
    assert "vitest.explorer" in extensions["recommendations"]


def test_vscode_does_not_recommend_vitest_extension_when_tests_disabled(
    tmp_path: Path,
):
    out = render(tmp_path / "p", with_tests=False)

    extensions = json.loads(
        (out / ".vscode" / "extensions.json").read_text(encoding="utf-8")
    )
    assert "vitest.explorer" not in extensions["recommendations"]


@pytest.mark.parametrize("manager", ["pnpm", "yarn", "bun"])
def test_package_json_pins_a_package_manager_for_corepack(tmp_path: Path, manager: str):
    out = render(tmp_path / manager, package_manager=manager)

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert manifest["packageManager"].startswith(f"{manager}@")


def test_package_json_has_no_package_manager_pin_for_npm(tmp_path: Path):
    out = render(tmp_path / "p", package_manager="npm")

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert "packageManager" not in manifest


@pytest.mark.parametrize("framework", ["none", "react"])
def test_biome_is_used_for_non_vue_frameworks(tmp_path: Path, framework: str):
    out = render(tmp_path / framework, framework=framework)

    assert (out / "biome.json").is_file()
    assert not (out / "eslint.config.mjs").exists()
    assert not (out / "prettier.config.mjs").exists()

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert "@biomejs/biome" in manifest["devDependencies"]
    assert "eslint" not in manifest["devDependencies"]
    assert "prettier" not in manifest["devDependencies"]
    assert manifest["scripts"]["lint"] == "biome lint ."
    assert manifest["scripts"]["format"] == "biome format --write ."


def test_eslint_and_prettier_are_kept_for_vue(tmp_path: Path):
    out = render(tmp_path / "p", framework="vue")

    assert (out / "eslint.config.mjs").is_file()
    assert (out / "prettier.config.mjs").is_file()
    assert not (out / "biome.json").exists()

    manifest = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert "@biomejs/biome" not in manifest["devDependencies"]
    assert "eslint" in manifest["devDependencies"]
    assert manifest["scripts"]["lint"] == "eslint ."


def test_vscode_recommends_biome_extension_for_non_vue(tmp_path: Path):
    out = render(tmp_path / "p", framework="react")

    extensions = json.loads(
        (out / ".vscode" / "extensions.json").read_text(encoding="utf-8")
    )
    assert "biomejs.biome" in extensions["recommendations"]
    assert "dbaeumer.vscode-eslint" not in extensions["recommendations"]
    assert "esbenp.prettier-vscode" not in extensions["recommendations"]

    settings = json.loads(
        (out / ".vscode" / "settings.json").read_text(encoding="utf-8")
    )
    assert settings["editor.defaultFormatter"] == "biomejs.biome"


def test_vscode_recommends_eslint_and_prettier_for_vue(tmp_path: Path):
    out = render(tmp_path / "p", framework="vue")

    extensions = json.loads(
        (out / ".vscode" / "extensions.json").read_text(encoding="utf-8")
    )
    assert "biomejs.biome" not in extensions["recommendations"]
    assert "dbaeumer.vscode-eslint" in extensions["recommendations"]
    assert "esbenp.prettier-vscode" in extensions["recommendations"]

    settings = json.loads(
        (out / ".vscode" / "settings.json").read_text(encoding="utf-8")
    )
    assert settings["editor.defaultFormatter"] == "esbenp.prettier-vscode"
