# Create a project

Start a new project from a template in the catalog. WOMM asks the template's
questions, writes the files, and optionally prepares the environment.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).
- A template identifier. `womm template list` shows the catalog;
  `official/python` and `official/javascript` ship with WOMM.
- For `--setup`: the runtime of the project (Python or Node.js) available on
  your machine. WOMM reports what is missing but installs nothing — see
  [Check what WOMM needs](check-dependencies.md).

## 📝 Steps

1. Pick a template and a destination:

    ```bash
    womm create official/python ./my-app
    ```

2. Answer the questions. Each template asks its own: project name, package
   name, minimum Python version, framework, license, and whether to include
   tests, coverage, CI and shared editor settings. The official templates also
   let you choose the linting, formatting and type-checking tools.

3. To also prepare the environment after rendering, add `--setup`:

    ```bash
    womm create official/python ./my-app --setup
    ```

    This creates the virtual environment, installs the dependencies and
    initializes git.

## ⚙️ Options

| Option             | Effect                                                          |
| :----------------- | :-------------------------------------------------------------- |
| `--data KEY=VALUE` | Pre-fill one answer, so it is not asked. Repeatable.            |
| `--defaults`       | Take the template defaults instead of prompting.                |
| `--force`          | Render into a destination that is not empty. Merges, see below. |
| `--pretend`        | Simulate: show what would be written, write nothing.            |
| `--setup`          | Prepare the environment after rendering.                        |
| `-v, --verbose`    | Show the detailed output.                                       |

Pre-filling and taking the defaults combine well for a scripted creation:

```bash
womm create official/javascript ./web --defaults \
  --data project_name=web --data framework=react --data typescript=true
```

### Choose development tools

| Template | Answer | Choices |
| :------- | :----- | :------ |
| Python | `tooling` | `ruff` (recommended), `black-isort` |
| Python | `type_checker` | `ty` (recommended), `mypy`, `pyright` |
| JavaScript/TypeScript | `tooling` | `biome` (recommended for plain JS/TS and React), `eslint-prettier` |
| JavaScript/TypeScript | `with_knip` | `true` to check unused files, exports and dependencies; default `false` |
| Both | `with_coverage` | Include coverage when tests are enabled; default `true` for Python, `false` for JS/TS |

Vue uses ESLint + Prettier; the template refuses Biome for this profile.
The Python `black-isort` profile keeps Ruff for linting and delegates formatting
and import sorting to Black and isort. The generated configurations, CI, hooks,
editor recommendations and README all follow your choices.

```bash
womm create official/python ./my-app --defaults \
  --data project_name=my-app --data tooling=black-isort --data type_checker=mypy

womm create official/javascript ./web --defaults \
  --data project_name=web --data framework=react --data typescript=true \
  --data tooling=eslint-prettier --data with_knip=true --data with_coverage=true
```

!!! warning "`--force` merges, it does not overwrite everything"

    `--force` allows rendering into a non-empty directory. Files the template
    produces replace their counterparts; everything else is left in place. Run
    the same command with `--pretend` first if you are unsure what it touches.

## ✅ Result

The destination holds the rendered project. With `--setup`, the environment is
ready and git is initialized.

The official templates record the WOMM version, template identifier and version,
and original choices in `.womm-template.json`. This file describes how the
project was generated; it is not an inventory of the current environment or a
Copier update file. To change an answer, create again into another destination.

### Keep tools and configurations compatible

Tools whose configurations are generated are pinned to versions validated
with the template. For Biome, the dependency and configuration schema have the
same version; Ruff rejects a version that differs from its `required-version`.
Install the project's dependencies and run its local tools rather than global
copies. Commit the generated lockfile and use it in CI.

Upgrade deliberately: review the tool's release notes, update its dependency pin
and any matching schema or version guard, adapt the configuration, update the
lockfile, then run the project's format, lint, type, test and build checks.
The generated README gives commands for the chosen tools and package manager.
For pip projects, exact tool pins do not lock transitive dependencies.

Upgrading WOMM changes the templates used for future projects. It does not
migrate existing projects or update their configurations.

If the command stops on a non-empty destination or on a missing runtime, see
[Troubleshooting](../troubleshooting.md#the-destination-is-not-empty).

## ➡️ Next steps

- [Manage templates](manage-templates.md) — register your own template.
- [The template catalog](../concepts/template-catalog.md) — official and user
  templates, and where the catalog lives.
