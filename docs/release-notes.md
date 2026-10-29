# Release notes

What changed for you, newest version first. The full technical history, commit
by commit, is in the [changelog](changelog.md).

## 4.0.0 — unreleased

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
