# Release notes

What changed for you, newest version first. The full technical history, commit
by commit, is in the [changelog](changelog.md).

## 5.6.0 — 2026-11-27

### Added

- `womm template init DESTINATION --from PROJECT` builds the template from an
  existing git project instead of an empty skeleton. Every tracked file is
  kept, and the project's names (`Flash-Excel`, `flash-excel`, `flash_excel`)
  become the `project_name`, `project_slug` and `package_name` questions.
  `--exclude PATTERN` leaves files out. Files likely to hold secrets are never
  taken. A report lists what was copied, changed and excluded. The template
  remembers its project in a `.womm-extract.json` file, which `update` needs.
- `womm template update` brings a template built with `--from` up to date
  with its project. Changes made only in the project are applied, your own
  edits are kept, and new files, deleted files and conflicts are asked with
  `-I`. `_womm.version` is raised by one patch when a file changed. TARGET can
  be a template directory as well as a registered template.
- WOMM keeps every version of a registered template's copy (`v1`, `v2`…)
  and renders from the latest. `womm template rollback NAME [VERSION]` renders
  from an older one, and `womm create NAME@vN` renders a version once.

## 5.5.0 — 2026-11-26

### Changed

- `womm template add` copies your template into `~/.womm` and renders from the
  copy, so moving or archiving the original no longer breaks the entry.
  `womm template update NAME` refreshes the copy from the original, and
  `remove` deletes the copy. Entries registered earlier keep pointing at
  their directory until you update them.
- Template identifiers are restricted to letters, digits, `.`, `_` and `-`
  in each part, since they now name directories.

## 5.4.0 — 2026-11-26

### New

- `womm template add`, `init`, `update` and `remove` take `-I`. WOMM asks for
  missing arguments, shows what it is about to write and waits for your
  confirmation; `init -I` offers to register the new skeleton.
- A user template identifier can carry one namespace, such as
  `neuraaak/my-python-project`. `official` and `user` are reserved.

### Fixed

- A user template kept in a git repository is rendered from its current state,
  uncommitted changes included and announced in a warning. It was rendered from
  its latest tag, silently ignoring later commits.
- `womm create --setup` works with user templates that declare
  `_womm.setup.language`, and a user template named like an official one no
  longer receives the official setup.
- `womm template list` and `show` follow edits to a user template's
  `copier.yml` without re-registering it, and `copier.yaml` is accepted.
- `womm template init` writes the description you give into the skeleton's
  catalog metadata, and the skeleton renders a README instead of a stray
  `.gitkeep`.
- The official templates check the project name when you answer: Python
  requires a valid distribution name and JavaScript a valid npm name. A name
  such as `My Project` used to break `uv sync` or `npm install` afterwards.
- `womm template init` refuses a template name that `womm template add` would
  refuse, instead of writing a README with commands that fail.
- `womm setup` titles its summary "Incomplete" when a step failed, instead of
  "Completed!" above the failure warnings.

## 5.3.0 — 2026-11-26

### New

- Official Python templates offer Ruff or Black + isort, and ty, mypy or
  Pyright. JavaScript templates offer Biome or ESLint + Prettier where
  supported, with optional Knip. Test coverage is optional in both templates.
- Generated projects record their template provenance and allow tool patches
  within the tested minor version. Lockfiles retain the exact resolved versions.
- `womm setup --update` updates declared tooling and reviewed configurations
  in official projects. Preview with `--dry-run`; block moves and destructive
  migrations require `--allow-destructive-actions`. Unknown transitions and
  conflicting values require manual review. Updates retain backups and a
  separate history; a failed installation restores files but may leave the
  environment needing synchronization. See
  [Update project tooling](tasks/configure-an-existing-project.md#update-an-official-projects-tooling).

## 5.2.0 — 2026-11-26

### New

- WOMM tells you when a newer version is published. A command run in a
  terminal ends with a line naming the new version and the command that
  upgrades your installation, and `womm` run alone shows whether you are up to
  date under its welcome panel. PyPI is checked at most once a day; set
  `WOMM_NO_UPDATE_CHECK` to turn the check off. See
  [Files and variables](reference/files-and-variables.md#new-release-notice).

## 5.1.1 — 2026-11-26

### Improved

- WOMM starts faster. `womm --version`, `-h` and every command run without its
  arguments answer in about 0.2 s instead of 1.4 s; the other commands save
  about 0.7 s.
- A command run without the arguments it requires, such as `womm create`,
  shows its help instead of a `Missing argument` error.

## 5.1.0 — 2026-11-24

!!! warning "Read before upgrading"

    - **Python projects managed by uv are set up with uv.** On a project with
      a `uv.lock` or a `[tool.uv]` table, `womm setup python` and
      `womm create --setup` run `uv sync` instead of `venv` and pip: the
      installed versions are those of the lockfile, and uv must be on your
      `PATH`.
    - **`womm setup` writes nothing without an option.** The VS Code
      configuration it used to write on every run is now the
      `--setup-vscode` step of `womm setup python` and `womm setup
      javascript`. `womm setup detect` detects the project and lists the
      steps; use `-I` for the guided setup.

### Improved

- `womm setup python` and `womm setup javascript` run without options list the
  available step options instead of reporting a completed setup.
- `womm create` without `--setup` tells you how to prepare the environment.
- `-h` works on every command, `womm context`, `womm deps` and `womm system`
  included.

### Fixed

- Python projects created with uv (the template default) pass their own CI
  after `womm create --setup`: it now writes the `uv.lock` the workflow
  requires, instead of a pip install without a lockfile.
- `--setup` uses the Python version the project asks for: a project needing a
  newer Python than WOMM's own was left without its dependencies.
- Python projects set up with pip are installed in editable mode, so code
  changes are visible without reinstalling.
- The GitHub Actions workflow of the Python template uses the current
  setup-uv and setup-python releases.

## 5.0.0 — 2026-11-24

!!! warning "Read before upgrading"

    - **`--setup-dev-tools` is gone** from `womm setup python` and
      `womm setup javascript`; Click now rejects it. Use `--install-deps`,
      which already installs the development dependencies the project
      declares.

### Improved

- `womm create --setup` and `womm setup javascript --install-deps` install
  with the project's own package manager: the `packageManager` field of
  `package.json`, then its lockfile, and npm otherwise. They no longer force
  npm on pnpm, Yarn or Bun projects.
- On a Python project, `--setup-git-hooks` now also runs `pre-commit install`
  when the project has a `.pre-commit-config.yaml`, with the `pre-commit` of
  its virtual environment.
- The setup summary lists only the steps that actually ran.

### Fixed

- On Windows, `womm create official/javascript --setup` installed nothing.
- Projects generated from the JavaScript template pass their own CI again:
  the Biome configuration was rejected, Vue projects failed the format check,
  Yarn projects linted Yarn's own files, and ESLint crashed on Vue projects
  installed with Yarn.
- `womm setup javascript` no longer adds ESLint, Prettier, Husky and
  lint-staged on top of the toolchain the template ships.

## 4.0.0 — 2026-10-29

!!! warning "Read before upgrading"

    This version changes how you install WOMM, how you create projects, and
    what WOMM does with data left by older installations. The three points
    below need an action from you.

    - **Install with uv or pip.** The self-installer and the standalone
      installer are gone. Install with `uv tool install womm-cli`, upgrade with
      `uv tool upgrade womm-cli`. The `womm install` and `womm uninstall`
      commands no longer exist.
    - **`womm create` takes a template, not a language.** Use
      `womm create official/python <destination>` instead of
      `womm create python`. `womm template list` shows what is available.
      There is no compatibility alias.
    - **Data left by an older self-installed WOMM is no longer migrated.** If
      your `~/.womm` still holds `.logs`, `.templates`, `.backup` or `.proof`,
      they stay where they are and are ignored. Move what you want to keep into
      `logs/`, `templates/` and `backups/` yourself.

### New

- `womm doctor` reports what your installation resolves — version, command,
  data directory, context menu entries — and changes nothing.
- `womm template` manages a catalog: list and inspect entries, register your own
  template under `user/`, scaffold a new one with `womm template init`.
- `womm create` accepts `--pretend` to simulate a render, `--data KEY=VALUE` to
  pre-fill one answer, and `--setup` to prepare the environment right after.
- `womm path backup` takes, lists, shows and restores PATH snapshots, and a
  snapshot is now taken automatically before every PATH change.
- `womm context backup cherry-pick` restores only the context menu entries you
  select.
- `womm deps` reports both strata — runtimes and runtime package managers — with
  versions, and exits non-zero when a requirement is missing.

### Improved

- Projects are rendered with [Copier](https://copier.readthedocs.io/), so
  templates ask real questions and you can register your own.
- The official Python template targets Python 3.13 and 3.14, with ruff, ty,
  pytest, pre-commit and a pinned GitHub Actions workflow; Django is optional
  and reads its secret key from the environment.
- The official JavaScript template targets Node.js 24 and 26, with Biome (ESLint
  and Prettier for Vue), Vite, Vitest, and the package manager of your choice.
- `~/.womm` holds data only — logs, templates and backups — never code.

### Fixed

- A project description containing a quote, a backslash, `{` or `<` no longer
  breaks the generated `pyproject.toml`, `package.json`, React and Vue
  components, or Python docstring.
- A generated Django project writes its database at the project root instead of
  inside `src/`, and ignores it in git.
- Generated projects derive their version from the package itself, so
  `pyproject.toml` and `__init__.py` cannot drift apart.

### Removed

- `womm lint` and `womm spell` — linting and spell checking belong to the
  project's own tooling, which the templates already configure.
- `--log-level`, `--log-file` and `--log-json`. They were accepted but never
  applied the setting they promised; Click now rejects them.
