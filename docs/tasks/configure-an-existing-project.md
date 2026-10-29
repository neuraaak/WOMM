# Configure an existing project

Add a development environment and tooling to a project you already have, without
re-creating it from a template.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).
- An existing project directory.
- The runtime of the project available: Python for a Python project, Node.js for
  a JavaScript one. See [Check what WOMM needs](check-dependencies.md).

## 📝 Steps

1. Let WOMM detect the project type:

    ```bash
    cd my-existing-project
    womm setup detect
    ```

2. Or name the language yourself:

    ```bash
    womm setup python
    womm setup javascript
    ```

3. Choose what to prepare. Every step is opt-in: run the command with the
   options for the steps you want, and nothing else happens.

    ```bash
    womm setup python --virtual-env --install-deps
    ```

    Run without options, WOMM detects and validates the project, then reports
    that no step was requested.

4. To be guided question by question, use the interactive mode:

    ```bash
    womm setup python --interactive
    ```

## ⚙️ Options

| Option                 | Effect                                                  | Available on                     |     |     |
| :--------------------- | :------------------------------------------------------ | :------------------------------- | --- | --- |
| `-p, --path DIRECTORY` | Work on this directory instead of the current one.      | `detect`, `python`, `javascript` |     |     |
| `-I, --interactive`    | Guided setup, one question at a time.                   | `detect`, `python`, `javascript` |     |     |
| `-v, --verbose`        | Show the detailed output.                               | `detect`, `python`, `javascript` |     |     |
| `--install-deps`       | Install the project dependencies.                       | `python`, `javascript`           |     |     |
| `--setup-dev-tools`    | Configure linting and formatting.                       | `python`, `javascript`           |     |     |
| `--setup-git-hooks`    | Install the git hooks.                                  | `python`, `javascript`           |     |     |
| `--virtual-env`        | Create the virtual environment.                         | `python`                         |     |     |
| `-t, --type TYPE`      | Force the project type: `javascript`, `react` or `vue`. | `javascript`                     |     |     |

## ✅ Result

The project has the environment and the tooling you asked for. WOMM reports each
step it ran and what it skipped.

If detection picks the wrong language, name it explicitly with `womm setup
python` or `womm setup javascript` — see
[Troubleshooting](../troubleshooting.md#womm-setup-detect-picks-the-wrong-language).

## ➡️ Next steps

- [Check what WOMM needs](check-dependencies.md) — when a step fails for a
  missing runtime.
