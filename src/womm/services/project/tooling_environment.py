"""Resolve, inspect and synchronize project-local tooling environments."""

from __future__ import annotations

import json
import os
import shutil

# This adapter executes project-local tooling.
import subprocess  # nosec B404
import tomllib
from pathlib import Path
from typing import Any

import json5
import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from womm.exceptions.project import ProjectServiceError

from .env_utils import detect_package_manager, uses_uv


def execute(
    command: list[str],
    project: Path,
    *,
    staging: bool = False,
    input_text: str | None = None,
) -> str:
    """Run a resolved executable, with an installation-sized timeout and no retries."""
    env = dict(os.environ)
    for name in (
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "UV_WORKING_DIR",
        "UV_PROJECT",
        "npm_config_global",
        "NPM_CONFIG_GLOBAL",
    ):
        env.pop(name, None)
    env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = "0"
    if staging:
        env["YARN_ENABLE_SCRIPTS"] = "false"
    try:
        # Executable paths are resolved below; arguments never pass through a shell.
        result = subprocess.run(  # nosec B603
            command,
            cwd=project,
            env=env,
            input=input_text,
            stdin=subprocess.DEVNULL if input_text is None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProjectServiceError(
            "tooling_command",
            "A tooling command could not complete; no automatic retry was attempted",
        ) from exc
    if result.returncode:
        # Package-manager output can contain private index URLs or config values.
        raise ProjectServiceError(
            "tooling_command",
            f"{Path(command[0]).stem} failed during tooling update; run the project's checks to inspect its diagnostics",
        )
    return result.stdout


class ToolingEnvironment:
    """One native package manager, operating on either the original or staged copy."""

    def __init__(self, project: Path, language: str) -> None:
        self.project = project
        self.language = language
        self.manager = (
            ("uv" if uses_uv(project) else "pip")
            if language == "python"
            else detect_package_manager(project)
        )
        if language == "python":
            self.manifest = "pyproject.toml"
            self.lockfiles = ["uv.lock"] if self.manager == "uv" else []
        else:
            self.manifest = "package.json"
            self.lockfiles = {
                "npm": ["package-lock.json"],
                "pnpm": ["pnpm-lock.yaml"],
                "yarn": ["yarn.lock"],
                "bun": ["bun.lock"],
            }[self.manager]

    @staticmethod
    def python(project: Path) -> Path:
        executable = (
            project
            / ".venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        if not executable.is_file() or not (project / ".venv").resolve().is_relative_to(
            project.resolve()
        ):
            raise ProjectServiceError(
                "tooling_environment",
                "A project-local .venv is required; run the project's setup first",
            )
        return executable

    def prefix(self) -> list[str]:
        manager = self.manager
        if manager == "yarn" and (corepack := shutil.which("corepack")):
            return [corepack, "yarn"]
        executable = shutil.which(manager)
        if executable is None:
            raise ProjectServiceError(
                "tooling_environment", f"{manager} is not available on PATH"
            )
        return [executable]

    def versions(self, project: Path, names: list[str]) -> dict[str, str]:
        """Prefer installed project versions, falling back to the native lockfile."""
        locked = self._locked_versions(project, names)
        installed: dict[str, str] = {}
        if self.language == "python" and (project / ".venv").exists():
            script = "import importlib.metadata as m,json,sys; from pathlib import Path; root=Path(sys.prefix).resolve(); print(json.dumps({d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions() if Path(d.locate_file('')).resolve().is_relative_to(root)}))"
            installed = json.loads(
                execute([str(self.python(project)), "-c", script], project)
            )
        elif self.language == "javascript":
            if self.manager == "yarn" and (project / ".pnp.cjs").exists():
                script = "const fs=require('fs'),pnp=require('pnpapi'),names=JSON.parse(process.argv[1]),out={}; for(const n of names){try{const p=pnp.resolveToUnqualified(n,process.cwd()+'/'); out[n]=JSON.parse(fs.readFileSync(p+'/package.json','utf8')).version;}catch{}} console.log(JSON.stringify(out));"
                installed = json.loads(
                    execute(
                        [*self.prefix(), "node", "-e", script, json.dumps(names)],
                        project,
                    )
                )
            else:
                for name in names:
                    path = project / "node_modules" / name / "package.json"
                    if path.is_file():
                        if not path.resolve().is_relative_to(project.resolve()):
                            raise ProjectServiceError(
                                "tooling_environment",
                                f"{name}: linked external tooling requires manual review",
                            )
                        installed[name] = str(
                            json.loads(path.read_text("utf-8"))["version"]
                        )
        for name in names:
            if name in locked and name in installed and locked[name] != installed[name]:
                raise ProjectServiceError(
                    "tooling_environment",
                    f"{name}: installed version differs from the lockfile; synchronize the project first",
                )
        return {name: installed.get(name, locked.get(name, "")) for name in names}

    def _locked_versions(self, project: Path, names: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        if not self.lockfiles or not (path := project / self.lockfiles[0]).is_file():
            return result
        text = path.read_text("utf-8")
        if self.manager == "uv":
            for package in tomllib.loads(text).get("package", []):
                name = canonicalize_name(package["name"])
                if name in names:
                    if name in result and result[name] != package["version"]:
                        raise ProjectServiceError(
                            "tooling_environment",
                            f"{name}: several locked versions require manual review",
                        )
                    result[name] = package["version"]
        elif self.manager == "npm":
            data = json.loads(text)
            for name in names:
                package = data.get("packages", {}).get(
                    f"node_modules/{name}", data.get("dependencies", {}).get(name, {})
                )
                if "version" in package:
                    result[name] = package["version"]
        elif self.manager == "pnpm":
            data = (
                yaml.safe_load(text)
                .get("importers", {})
                .get(".", {})
                .get("devDependencies", {})
            )
            result = {
                name: str(data[name]["version"]).split("(", 1)[0]
                for name in names
                if name in data
            }
        elif self.manager == "yarn":
            if "# yarn lockfile v1" in text:
                raise ProjectServiceError(
                    "tooling_environment",
                    "Yarn Classic updates require manual review; official templates use modern Yarn",
                )
            data = yaml.safe_load(text)
            manifest = json.loads((project / "package.json").read_text("utf-8"))
            for name in names:
                selector = f"{name}@npm:{manifest['devDependencies'][name]}"
                for key, package in data.items():
                    if selector in key.split(", ") and isinstance(package, dict):
                        result[name] = str(package["version"])
        elif self.manager == "bun":
            data = json5.loads(text).get("packages", {})
            result = {
                name: data[name][0].rsplit("@", 1)[1] for name in names if name in data
            }
        return result

    def resolve(self, stage: Path, names: list[str]) -> dict[str, str]:
        """Install into the disposable copy; never upgrade the user's environment here."""
        if self.manager == "uv":
            args = [*self.prefix(), "sync", "--group", "dev", "--no-install-project"]
            for name in names:
                args.extend(["--upgrade-package", name])
            execute(args, stage, staging=True)
        elif self.manager == "pip":
            self._resolve_pip(stage, names)
        else:
            manifest_path = stage / self.manifest
            manifest = manifest_path.read_bytes()
            operation = "up" if self.manager == "yarn" else "update"
            args = [*self.prefix(), operation]
            args.extend(["-R"] if self.manager == "yarn" else ["--ignore-scripts"])
            execute([*args, *names], stage, staging=True)
            # pnpm/Bun may save a newer patch floor. WOMM owns the bounds;
            # restore their spelling and align the native lockfile with it.
            manifest_path.write_bytes(manifest)
            install = (
                ["install"]
                if self.manager == "yarn"
                else ["install", "--ignore-scripts"]
            )
            execute([*self.prefix(), *install], stage, staging=True)
            if json.loads(manifest_path.read_bytes()) != json.loads(manifest):
                raise ProjectServiceError(
                    "tooling_environment",
                    "The package manager changed unrelated manifest settings; manual review is required",
                )
            manifest_path.write_bytes(manifest)
        return self.versions(stage, names)

    def _resolve_pip(self, stage: Path, names: list[str]) -> None:
        original = self.python(self.project)
        execute(
            [str(original), "-m", "venv", str(stage / ".venv")], stage, staging=True
        )
        python = str(self.python(stage))
        execute(
            [python, "-m", "pip", "install", "--upgrade", "pip>=25.1"],
            stage,
            staging=True,
        )
        # Preserve unrelated direct dependencies rather than upgrading the whole venv.
        installed = self.versions(
            self.project, list(self._all_python_requirements(self.project))
        )
        constraints = stage / ".womm-update-constraints.txt"
        constraints.write_text(
            "\n".join(
                f"{name}=={version}"
                for name, version in installed.items()
                if name not in names and version
            ),
            encoding="utf-8",
        )
        execute(
            [python, "-m", "pip", "install", "--group", "dev", "-c", str(constraints)],
            stage,
            staging=True,
        )
        runtime = (
            tomllib.loads((stage / "pyproject.toml").read_text("utf-8"))
            .get("project", {})
            .get("dependencies", [])
        )
        if runtime:
            execute(
                [python, "-m", "pip", "install", "-c", str(constraints), *runtime],
                stage,
                staging=True,
            )

    @staticmethod
    def _all_python_requirements(project: Path) -> set[str]:
        data = tomllib.loads((project / "pyproject.toml").read_text("utf-8"))
        requirements = list(data.get("project", {}).get("dependencies", []))
        for values in data.get("dependency-groups", {}).values():
            requirements.extend(value for value in values if isinstance(value, str))
        return {canonicalize_name(Requirement(value).name) for value in requirements}

    def synchronize(self, project: Path, stage: Path, names: list[str]) -> None:
        """Install the already-resolved lockfile or exact pip versions."""
        if self.manager == "uv":
            command = [*self.prefix(), "sync", "--locked", "--group", "dev"]
        elif self.manager == "pip":
            exact = self.versions(stage, names)
            groups = tomllib.loads((stage / "pyproject.toml").read_text("utf-8"))[
                "dependency-groups"
            ]

            def requirements(group: str):
                for entry in groups[group]:
                    if isinstance(entry, str):
                        yield Requirement(entry)
                    else:
                        yield from requirements(entry["include-group"])

            selected = []
            for requirement in requirements("dev"):
                name = canonicalize_name(requirement.name)
                if name in exact:
                    extras = (
                        f"[{','.join(sorted(requirement.extras))}]"
                        if requirement.extras
                        else ""
                    )
                    selected.append(f"{name}{extras}=={exact[name]}")
            constraints = stage / ".womm-resolved-constraints.txt"
            constraints.write_text(
                execute([str(self.python(stage)), "-m", "pip", "freeze"], stage),
                encoding="utf-8",
            )
            command = [
                str(self.python(project)),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "-c",
                str(constraints),
                *selected,
            ]
        else:
            frozen = {
                "npm": ["ci"],
                "pnpm": ["install", "--frozen-lockfile"],
                "yarn": ["install", "--immutable"],
                "bun": ["install", "--frozen-lockfile"],
            }
            command = [*self.prefix(), *frozen[self.manager]]
        execute(command, project)

    def tool(
        self,
        project: Path,
        name: str,
        args: list[str],
        *,
        input_text: str | None = None,
    ) -> str:
        if self.language == "python":
            executable = self.python(project).parent / (
                name + (".exe" if os.name == "nt" else "")
            )
            if not executable.is_file():
                raise ProjectServiceError(
                    "tooling_validation", f"{name}: project-local executable not found"
                )
            command = [str(executable), *args]
        elif self.manager == "yarn":
            command = [*self.prefix(), "exec", name, *args]
        else:
            executable = (
                project
                / "node_modules"
                / ".bin"
                / (
                    name
                    + (
                        (".exe" if self.manager == "bun" else ".cmd")
                        if os.name == "nt"
                        else ""
                    )
                )
            )
            if not executable.is_file():
                raise ProjectServiceError(
                    "tooling_validation", f"{name}: project-local executable not found"
                )
            command = [str(executable), *args]
        return execute(command, project, staging=True, input_text=input_text)

    def validate(self, stage: Path, names: list[str], registry: dict[str, Any]) -> None:
        """Validate configuration with the target tools, without fixing user code."""
        probe = stage / "__womm_update_probe__.py"
        probe.write_text("", encoding="utf-8")
        js_probe = stage / "__womm_update_probe__.js"
        js_probe.write_text("", encoding="utf-8")
        commands = {
            "ruff": ["check", "--show-settings", str(probe)],
            "black": [
                "--check",
                "--code",
                "",
                "--config",
                str(stage / "pyproject.toml"),
            ],
            "isort": ["--show-config", "--settings-path", str(stage)],
            "ty": ["check", str(probe), "--project", str(stage)],
            "mypy": ["--config-file", str(stage / "pyproject.toml"), str(probe)],
            "pyright": ["--project", str(stage), str(probe)],
            "biome": [
                "check",
                "--formatter-enabled=false",
                "--assist-enabled=false",
                str(js_probe),
            ],
            "eslint": ["--print-config", "src/__womm_update_probe__.js"],
            "prettier": ["--check", str(js_probe)],
            "typescript": ["--showConfig", "--project", str(stage / "tsconfig.json")],
        }
        for name in names:
            validator = registry[name].get("validate")
            if validator in commands:
                self.tool(
                    stage,
                    "tsc" if validator == "typescript" else validator,
                    commands[validator],
                )
