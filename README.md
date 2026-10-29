# 🛠️ Works On My Machine (WOMM)

[![PyPI version](https://img.shields.io/pypi/v/womm-cli?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/womm-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/womm-cli?style=flat&logo=python&logoColor=white)](https://pypi.org/project/womm-cli/)
[![PyPI status](https://img.shields.io/pypi/status/womm-cli?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/womm-cli/)
[![CI](https://img.shields.io/github/actions/workflow/status/neuraaak/WOMM/01-ci.yml?style=flat&label=ci&logo=githubactions&logoColor=white)](https://github.com/neuraaak/WOMM/actions/workflows/01-ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue?style=flat&logo=materialformkdocs&logoColor=white)](https://neuraaak.github.io/WOMM/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat&logo=github&logoColor=white)](https://github.com/neuraaak/WOMM/blob/main/LICENSE)
[![packaging](https://img.shields.io/badge/packaging-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![lint](https://img.shields.io/badge/lint-ruff-D7FF64?style=flat&logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)
[![types](https://img.shields.io/badge/types-ty-261230?style=flat&logo=astral&logoColor=white)](https://github.com/astral-sh/ty)
[![tests](https://img.shields.io/badge/tests-pytest-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)

![Logo](https://raw.githubusercontent.com/neuraaak/WOMM/main/docs/assets/logo-min.png)

**WOMM** is a command-line tool that creates Python and JavaScript projects from
templates, configures existing ones, and keeps your PATH and Windows context
menu under control.

> **Installed as `womm-cli`, used as `womm`.** The name `womm` was already taken
> on PyPI, so the package is published as `womm-cli`. You only type that name to
> install or upgrade. The former name `works-on-my-machine` is no longer
> maintained: its last release, `3.2.4`, exists only to carry that notice.

---

## 📦 Installation

```bash
# Recommended: isolated install, uv provisions Python if needed
uv tool install womm-cli
uv tool update-shell   # once, if `womm` is not on your PATH yet

# Any other PEP 517 installer works on the same wheel
pipx install womm-cli
pip install --user womm-cli

# Run it without installing anything
uvx womm-cli --help

# Unreleased code, straight from the repository
uv tool install git+https://github.com/neuraaak/WOMM.git
```

Upgrade with `uv tool upgrade womm-cli`, remove with
`uv tool uninstall womm-cli`. Neither touches your data in `~/.womm`.

Requires Python 3.13 or later — `uv tool install` provisions it for you.

---

## 🚀 Quick Start

```bash
# Create a Python project, then prepare its environment
womm create official/python ./hello-womm --setup

# Configure a project you already have
cd my-existing-project
womm setup detect

# Check what WOMM resolves on this machine
womm doctor
```

---

## 🎯 Key Features

- ✅ Project creation from [Copier](https://copier.readthedocs.io/) templates,
  with real questions and a catalog you can extend
- ✅ Two official templates: Python (optional Django) and JavaScript/TypeScript
  (optional React or Vue)
- ✅ Environment setup for existing projects: virtual environment, dependencies,
  dev tooling, git hooks
- ✅ PATH management, with an automatic backup before every change
- ✅ Windows context menu entries, with backups and selective restore
- ✅ Read-only dependency report across runtimes and package managers
- ✅ User data kept in `~/.womm`, untouched by upgrades

---

## 💻 CLI Usage

```bash
womm create TEMPLATE DESTINATION    # render a catalog template
womm setup detect|python|javascript # configure an existing project
womm template list|show|add|init|update|remove
womm deps check|status|list         # report runtimes and package managers
womm path list|add|remove|backup    # inspect and manage your PATH
womm context register|list|unregister|quick-setup|backup  # Windows only
womm system detect|refresh-env      # system information, Windows refresh
womm doctor                         # what this installation resolves
```

Every command takes `-h` for its own options. The full list is in the
[command reference](https://neuraaak.github.io/WOMM/reference/commands/).

---

## 📚 Documentation

Complete documentation is available at
**[neuraaak.github.io/WOMM](https://neuraaak.github.io/WOMM/)**

| Section                                                                    | Description                                   |
| -------------------------------------------------------------------------- | --------------------------------------------- |
| **[Get started](https://neuraaak.github.io/WOMM/get-started/)**            | Install WOMM and create your first project    |
| **[Guides](https://neuraaak.github.io/WOMM/tasks/)**                       | One page per task, from creation to the PATH  |
| **[Concepts](https://neuraaak.github.io/WOMM/concepts/template-catalog/)** | The template catalog, dependencies, your data |
| **[Reference](https://neuraaak.github.io/WOMM/reference/commands/)**       | Every command, option, file and variable      |
| **[Troubleshooting](https://neuraaak.github.io/WOMM/troubleshooting/)**    | Symptoms, causes and fixes                    |
| **[FAQ](https://neuraaak.github.io/WOMM/faq/)**                            | Short answers to recurring questions          |
| **[Release notes](https://neuraaak.github.io/WOMM/release-notes/)**        | What changed for you in each version          |

---

## 🧪 Testing

```bash
uv run pytest                 # unit tests with coverage
uv run pytest tests/unit -q   # quick run
```

---

## 🛠️ Development Setup

```bash
git clone https://github.com/neuraaak/WOMM.git
cd WOMM

uv sync --group dev        # install the project and its dev tooling
uv run pre-commit install  # enable the git hooks

uv run ruff check .        # lint
uv run ruff format .       # format
uv run ty check .          # type check
uv run lint-imports        # layer contracts
uv run mkdocs serve        # preview the documentation
```

---

## 📦 Dependencies

| Dependency | Constraint       | Role                       |
| ---------- | ---------------- | -------------------------- |
| click      | `>=8.0.0`        | Command-line interface     |
| rich       | `>=13.0.0`       | Terminal rendering         |
| ezplog     | `>=2.0.0,<3.0.0` | Logging and console output |
| InquirerPy | `>=0.3.4`        | Interactive prompts        |
| copier     | `>=9.17,<10`     | Template rendering         |

External programs WOMM reports on but never installs: Python 3.13+, Node.js
18+, git 2.30+, and one of pip, uv, npm or yarn.

---

## 📝 License

Released under the [MIT License](https://github.com/neuraaak/WOMM/blob/main/LICENSE).

---

## 🔗 Links

- **Repository** — [github.com/neuraaak/WOMM](https://github.com/neuraaak/WOMM)
- **PyPI** — [pypi.org/project/womm-cli](https://pypi.org/project/womm-cli/)
- **Documentation** — [neuraaak.github.io/WOMM](https://neuraaak.github.io/WOMM/)
- **Issues** — [github.com/neuraaak/WOMM/issues](https://github.com/neuraaak/WOMM/issues)

---

**WOMM** – Scaffold it once, run it anywhere.
