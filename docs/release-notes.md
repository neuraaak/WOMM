# Release notes

What changed for you, newest version first. The full technical history, commit
by commit, is in the [changelog](changelog.md).

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
