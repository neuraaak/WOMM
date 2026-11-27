#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE EXTRACTION SERVICE - Copier template from a project
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Turn an existing git project into the content of a Copier template.

The template is a faithful snapshot of the project's tracked files. Only the
project's own names become template variables; every other byte is kept.
Rendered files use dedicated Jinja delimiters and a dedicated suffix, so that
GitHub expressions, Jinja sources and TOML arrays of tables stay plain text.

Everything is checked before anything is written: a refusal leaves the
destination untouched. The extraction never runs a file of the project.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
import json
import re
import shutil
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from womm.exceptions.project import ProjectServiceError
from womm.shared.results.template_results import TemplateExtractionReport

from ..common.command_runner_service import CommandRunnerService

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

# Suffix of the files Copier renders; files without it are copied verbatim.
TEMPLATE_SUFFIX = ".womm"

# Copier ``_envops``: rare enough to never meet in a project's own files.
DELIMITERS = {
    "variable_start_string": "[[@",
    "variable_end_string": "@]]",
    "block_start_string": "[%@",
    "block_end_string": "@%]",
    "comment_start_string": "[#@",
    "comment_end_string": "@#]",
}

# Directories never taken, whatever ``--exclude`` says.
FORCED_DIRS = frozenset({".git", ".shared-session", ".womm"})

# Files likely to hold credentials, matched case-insensitively on each path
# part. They are excluded before any read. ``*credentials*`` also drops a
# legitimate ``test_credentials.py``: that cost is accepted and reported.
RISK_PATTERNS = (
    ".env",
    ".env.*",
    ".envrc",
    ".netrc",
    "_netrc",
    ".npmrc",
    ".pypirc",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "id_rsa*",
    "id_ed25519*",
    "*credentials*",
    "*service-account*.json",
    ".aws",
    ".ssh",
    ".gnupg",
    ".kube",
    ".tufup",
    ".tufup-repo-config",
)
RISK_PATHS = ("*/.docker/config.json", ".docker/config.json")
RISK_ALLOWED = frozenset({".env.example", "example.env"})

# Directories that never hold the project's own package.
NOT_PACKAGE_DIRS = frozenset({"build", "dist", "node_modules", "tests", "docs"})

# Lockfiles pin the source project's state; ``--frozen`` needs them regenerated.
LOCKFILES = frozenset(
    {
        "uv.lock",
        "poetry.lock",
        "pdm.lock",
        "Pipfile.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
    }
)

# A name is replaced only between characters that cannot continue it.
NAME_CHAR = "A-Za-z0-9_-"

# Git index modes left out: symbolic links and submodules.
GIT_MODE_SYMLINK = "120000"
GIT_MODE_GITLINK = "160000"

MAX_RESIDUALS = 50

# ///////////////////////////////////////////////////////////////
# MODELS
# ///////////////////////////////////////////////////////////////


@dataclass
class ExtractedFile:
    """One file of the template, ready to be written."""

    source: PurePosixPath
    target: PurePosixPath
    content: bytes | None = None  # None: copied from the source as is


@dataclass
class ExtractionPlan:
    """Everything the extraction will write, computed without writing."""

    source: Path
    files: list[ExtractedFile] = field(default_factory=list)
    report: TemplateExtractionReport = field(default_factory=TemplateExtractionReport)

    @property
    def meta_answers(self) -> dict[str, str]:
        """Answers telling the meta-template which variables exist."""
        return {
            "has_identity": str(bool(self.report.variables)).lower(),
            "has_package": str("package_name" in self.report.variables).lower(),
        }


# ///////////////////////////////////////////////////////////////
# SERVICE
# ///////////////////////////////////////////////////////////////


class TemplateExtractionService:
    """Plan, then write, the snapshot of a project as template content."""

    def __init__(self) -> None:
        self._runner = CommandRunnerService()

    # ///////////////////////////////////////////////////////////
    # PUBLIC METHODS
    # ///////////////////////////////////////////////////////////

    def plan(
        self, source: Path, destination: Path, excludes: Sequence[str] = ()
    ) -> ExtractionPlan:
        """Compute the extraction without writing anything.

        Args:
            source: Root of the git repository to extract.
            destination: Template directory that will receive the snapshot.
            excludes: fnmatch patterns on POSIX relative paths; a trailing
                ``/`` targets a directory and everything below it.

        Returns:
            ExtractionPlan: Files to write and the report.

        Raises:
            ProjectServiceError: When the extraction must be refused.
        """
        source = source.resolve()
        destination = destination.resolve()
        if destination == source or source.is_relative_to(destination):
            raise _refuse(
                "The template destination cannot be the project or one of its parents"
            )
        self._require_repository_root(source)
        entries = self._tracked_entries(source)

        plan = ExtractionPlan(source=source)
        report = plan.report
        matched: set[str] = set()
        kept: list[PurePosixPath] = []
        for mode, rel in entries:
            reason = self._exclusion_reason(source, destination, rel, mode)
            if reason is None:
                reason = _user_exclusion(rel, excludes, matched)
            if reason is None:
                kept.append(rel)
            else:
                report.excluded.append((rel.as_posix(), reason))
        report.warnings.extend(
            f"--exclude {pattern} matched no tracked file"
            for pattern in excludes
            if pattern not in matched
        )

        variants = self._identity(source, kept, report)
        pattern = _variants_pattern(variants)
        self._check_paths(kept)

        for rel in kept:
            target = PurePosixPath(
                *(_replace(part, pattern, variants, report) for part in rel.parts)
            )
            content = self._transform(source / rel, rel, pattern, variants, report)
            if content is not None:
                # Copier renders every path, but only suffixed contents.
                target = target.with_name(target.name + TEMPLATE_SUFFIX)
            if content is not None or target != rel:
                report.transformed.append(rel.as_posix())
            else:
                report.copied.append(rel.as_posix())
            plan.files.append(ExtractedFile(source=rel, target=target, content=content))
        _check_render_collisions(plan.files)

        if report.transformed:
            report.warnings.append(
                "Files with replaced names are rendered with LF line endings"
            )
        report.warnings.append(
            "Version, description, authors, URLs, license and publishing settings"
            " are kept as in the project: review them"
        )
        if any(rel.name in LOCKFILES for rel in kept):
            report.warnings.append(
                "Lockfiles are kept: regenerate them in a new project before any --frozen install"
            )
        return plan

    def write(self, plan: ExtractionPlan, template_dir: Path) -> None:
        """Write the planned files under ``template_dir``.

        Args:
            plan: Result of :meth:`plan`.
            template_dir: Copier ``_subdirectory`` of the new template.
        """
        for item in plan.files:
            origin = plan.source / item.source
            target = template_dir / item.target
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.content is None:
                shutil.copy2(origin, target)
            else:
                target.write_bytes(item.content)
                shutil.copymode(origin, target)

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - LISTING
    # ///////////////////////////////////////////////////////////

    def _git(self, source: Path, *args: str) -> str:
        result = self._runner.run(["git", "-C", str(source), *args])
        if not result:
            # Git's own message: "dubious ownership" is not "not a repository".
            raise _refuse(f"git {args[0]} failed", details=result.stderr.strip())
        return result.stdout

    def _require_repository_root(self, source: Path) -> None:
        top = Path(self._git(source, "rev-parse", "--show-toplevel").strip())
        if top.resolve() != source:
            raise _refuse(
                "--from must be the root of a git repository",
                details=f"The repository root is {top}",
            )

    def _tracked_entries(self, source: Path) -> list[tuple[str, PurePosixPath]]:
        entries: list[tuple[str, PurePosixPath]] = []
        for record in self._git(source, "ls-files", "-z", "-s").split("\0"):
            if not record:
                continue
            meta, path = record.split("\t", 1)
            mode, _sha, stage = meta.split()
            if stage != "0":
                raise _refuse(
                    "The project has unmerged files", details=f"Resolve {path} first"
                )
            entries.append((mode, PurePosixPath(path)))
        return entries

    def _exclusion_reason(
        self,
        source: Path,
        destination: Path,
        rel: PurePosixPath,
        mode: str,
    ) -> str | None:
        if rel.parts[0] in FORCED_DIRS:
            return "WOMM or git internal"
        path = source / rel
        if path.is_relative_to(destination):
            return "inside the template destination"
        if _is_risky(rel):
            return "file at risk of holding secrets"
        if mode == GIT_MODE_GITLINK:
            return "git submodule"
        if mode == GIT_MODE_SYMLINK:
            return "symbolic link"
        current = source
        for part in rel.parts:
            current = current / part
            if current.is_symlink() or current.is_junction():
                return "symbolic link or junction on disk"
        if not path.is_file():
            return "tracked but missing from the working tree"
        if not path.resolve().is_relative_to(source):
            return "resolves outside the project"
        return None

    def _check_paths(self, kept: list[PurePosixPath]) -> None:
        for rel in kept:
            for part in rel.parts:
                if part.endswith(TEMPLATE_SUFFIX):
                    raise _refuse(
                        f"{rel} ends with {TEMPLATE_SUFFIX}, the template suffix",
                        details="Exclude it with --exclude or rename it.",
                    )
                if _has_delimiter(part):
                    raise _refuse(f"{rel} contains a template delimiter")

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - IDENTITY
    # ///////////////////////////////////////////////////////////

    def _identity(
        self,
        source: Path,
        kept: list[PurePosixPath],
        report: TemplateExtractionReport,
    ) -> dict[str, str]:
        """Map each project name variant to the variable replacing it."""
        names = {rel.as_posix() for rel in kept}
        distribution = None
        if "pyproject.toml" in names:
            try:
                data = tomllib.loads((source / "pyproject.toml").read_text("utf-8-sig"))
            except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
                raise _refuse(
                    "pyproject.toml cannot be parsed", details=str(exc)
                ) from exc
            distribution = data.get("project", {}).get("name")
        elif "package.json" in names:
            try:
                data = json.loads((source / "package.json").read_text("utf-8-sig"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _refuse(
                    "package.json cannot be parsed", details=str(exc)
                ) from exc
            distribution = data.get("name")
            if isinstance(distribution, str) and distribution.startswith("@"):
                report.warnings.append(
                    f"Scoped package name {distribution} is not supported: names kept as is"
                )
                distribution = None
        if not isinstance(distribution, str) or not distribution:
            report.warnings.append("No project name found: names kept as is")
            return {}

        slug = re.sub(r"[-_.]+", "-", distribution).lower()
        package = _find_package(names, slug)
        if package is None:
            report.warnings.append(
                "No unique Python package found: its name is kept as is"
            )

        # Equal strings: the most constrained variable wins, since its value
        # is valid wherever the others are expected.
        variants: dict[str, str] = {distribution: "project_name", slug: "project_slug"}
        if package is not None:
            variants[package] = "package_name"
        if variants[distribution] != "project_name":
            report.warnings.append(
                f"{distribution} is also the {variants[distribution].replace('_', ' ')}:"
                f" it is replaced by {variants[distribution]}, not project_name"
            )
        report.variables = {var: name for name, var in variants.items()}
        report.replacements = dict.fromkeys(report.variables, 0)
        return variants

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - CONTENT
    # ///////////////////////////////////////////////////////////

    def _transform(
        self,
        path: Path,
        rel: PurePosixPath,
        pattern: re.Pattern[str] | None,
        variants: dict[str, str],
        report: TemplateExtractionReport,
    ) -> bytes | None:
        """Return the rendered-to-be content, or None to copy the file as is."""
        if pattern is None:
            return None
        data = path.read_bytes()
        if b"\0" in data:
            return None
        try:
            text = data.decode("utf-8")  # a BOM survives as U+FEFF
        except UnicodeDecodeError:
            return None
        replaced = _replace(text, pattern, variants, report)
        _record_residuals(rel, replaced, variants, report)
        if replaced == text:
            return None
        if _has_delimiter(text):
            raise _refuse(
                f"{rel} contains a template delimiter",
                details="Exclude it with --exclude.",
            )
        return replaced.encode("utf-8")


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS
# ///////////////////////////////////////////////////////////////


def _refuse(reason: str, details: str = "") -> ProjectServiceError:
    return ProjectServiceError(
        operation="extract_template", reason=reason, details=details
    )


def _is_risky(rel: PurePosixPath) -> bool:
    if any(fnmatchcase(rel.as_posix().lower(), p) for p in RISK_PATHS):
        return True
    for part in rel.parts:
        lowered = part.lower()
        if lowered in RISK_ALLOWED:
            continue
        if any(fnmatchcase(lowered, p) for p in RISK_PATTERNS):
            return True
    return False


def _user_exclusion(
    rel: PurePosixPath, excludes: Sequence[str], matched: set[str]
) -> str | None:
    posix = rel.as_posix()
    for pattern in excludes:
        if pattern.endswith("/"):
            hit = any(
                fnmatchcase(parent.as_posix(), pattern.rstrip("/"))
                for parent in rel.parents
                if parent.parts
            )
        else:
            hit = fnmatchcase(posix, pattern)
        if hit:
            matched.add(pattern)
            return f"--exclude {pattern}"
    return None


def _find_package(names: set[str], slug: str) -> str | None:
    """The unique package under ``src/``, else the root one named after the slug."""
    under_src = {
        parts[1]
        for parts in (PurePosixPath(n).parts for n in names)
        if len(parts) == 3 and parts[0] == "src" and parts[2] == "__init__.py"
    }
    under_src = {p for p in under_src if not p.startswith(".")}
    if len(under_src) == 1:
        return under_src.pop()
    if under_src:
        return None
    root = slug.replace("-", "_")
    if root not in NOT_PACKAGE_DIRS and f"{root}/__init__.py" in names:
        return root
    return None


def _variants_pattern(variants: dict[str, str]) -> re.Pattern[str] | None:
    if not variants:
        return None
    alternation = "|".join(
        re.escape(name) for name in sorted(variants, key=len, reverse=True)
    )
    return re.compile(rf"(?<![{NAME_CHAR}])(?:{alternation})(?![{NAME_CHAR}])")


def _replace(
    text: str,
    pattern: re.Pattern[str] | None,
    variants: dict[str, str],
    report: TemplateExtractionReport,
) -> str:
    if pattern is None:
        return text

    def placeholder(match: re.Match[str]) -> str:
        variable = variants[match.group(0)]
        report.replacements[variable] += 1
        return f"{DELIMITERS['variable_start_string']} {variable} {DELIMITERS['variable_end_string']}"

    return pattern.sub(placeholder, text)


def _record_residuals(
    rel: PurePosixPath,
    text: str,
    variants: dict[str, str],
    report: TemplateExtractionReport,
) -> None:
    """Note the name variants the bounded replacement left in place."""
    if report.residuals_truncated:
        return
    loose = re.compile("|".join(re.escape(name) for name in variants), re.IGNORECASE)
    for number, line in enumerate(text.splitlines(), start=1):
        if loose.search(line):
            if len(report.residuals) >= MAX_RESIDUALS:
                report.residuals_truncated = True
                return
            report.residuals.append(f"{rel}:{number}")


def _check_render_collisions(files: list[ExtractedFile]) -> None:
    """Refuse paths that some answers would render to the same path.

    project_name, project_slug and package_name render alike for a name such
    as ``app``, so two paths that differ only by these variables, by case or
    by the template suffix are one path for Copier: the last would overwrite
    the first.
    """
    variable = re.compile(
        re.escape(DELIMITERS["variable_start_string"])
        + r" \w+ "
        + re.escape(DELIMITERS["variable_end_string"])
    )

    def canonical(path: PurePosixPath) -> str:
        posix = path.as_posix().removesuffix(TEMPLATE_SUFFIX)
        return variable.sub("<variable>", posix).casefold()

    files_by_path: dict[str, PurePosixPath] = {}
    for item in files:
        key = canonical(item.target)
        clash = files_by_path.setdefault(key, item.source)
        if clash != item.source:
            raise _refuse(
                f"{item.source} and {clash} can render to the same path",
                details="Exclude or rename one of them.",
            )
    for item in files:
        for parent in item.target.parents:
            clash = files_by_path.get(canonical(parent)) if parent.parts else None
            if clash is not None:
                raise _refuse(
                    f"{item.source} and {clash} can render to the same path",
                    details="Exclude or rename one of them.",
                )


def _has_delimiter(text: str) -> bool:
    return any(token in text for token in DELIMITERS.values())


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "DELIMITERS",
    "TEMPLATE_SUFFIX",
    "ExtractedFile",
    "ExtractionPlan",
    "TemplateExtractionService",
]
