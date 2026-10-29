# Get started with WOMM

By the end of this page you will have WOMM installed and a Python project
created from a template, with its virtual environment, its dependencies and a
git repository already in place.

## 🔧 Prerequisites

- Windows, macOS or Linux.
- [uv](https://docs.astral.sh/uv/). If you do not have it:

    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
    curl -LsSf https://astral.sh/uv/install.sh | sh                                      # macOS, Linux
    ```

!!! note "Python is not a prerequisite"

    `uv tool install` downloads the Python version WOMM needs. You do not have
    to install Python yourself.

## 📝 Steps

1. Install WOMM as an isolated tool:

    ```bash
    uv tool install womm-cli
    ```

    The command is named `womm`. The package is named `womm-cli` because the
    name `womm` was already taken on PyPI.

2. If your shell answers `womm: command not found`, add the tool directory to
   your PATH, then open a new terminal:

    ```bash
    uv tool update-shell
    ```

3. Check what WOMM sees:

    ```bash
    womm doctor
    ```

    The report shows the version, the executable your shell resolves, and the
    data directory WOMM will use.

4. Create your first project:

    ```bash
    womm create official/python ./hello-womm --setup
    ```

    WOMM asks for the project name, the package name, the Python version and
    the options of the template. `--setup` prepares the environment once the
    files are written: virtual environment, dependencies, git repository.

## ✅ Result

`./hello-womm` holds a complete Python project: `pyproject.toml` with ruff and
ty configured, a test suite, a GitHub Actions workflow, and a `.venv` ready to
use. Running `womm doctor` again shows the same installation, unchanged — WOMM
keeps its own data in `~/.womm` and never writes into your projects after
creation.

## ➡️ Next steps

- [Create a project](tasks/create-a-project.md) — every option of
  `womm create`, including simulating a render.
- [Configure an existing project](tasks/configure-an-existing-project.md) — for
  a project you did not create with WOMM.
- [The template catalog](concepts/template-catalog.md) — what templates are
  available and how to add your own.
- [Troubleshooting](troubleshooting.md) — if any step above did not behave as
  described.
