# WOMM

[![CI](https://img.shields.io/github/actions/workflow/status/neuraaak/WOMM/01-ci.yml?style=flat&label=ci&logo=githubactions&logoColor=white)](https://github.com/neuraaak/WOMM/actions/workflows/01-ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue?style=flat&logo=materialformkdocs&logoColor=white)](https://neuraaak.github.io/WOMM/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat&logo=github&logoColor=white)](https://github.com/neuraaak/WOMM/blob/main/LICENSE)
[![packaging](https://img.shields.io/badge/packaging-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![lint](https://img.shields.io/badge/lint-ruff-D7FF64?style=flat&logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)
[![types](https://img.shields.io/badge/types-ty-261230?style=flat&logo=astral&logoColor=white)](https://github.com/astral-sh/ty)
[![tests](https://img.shields.io/badge/tests-pytest-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)

**Works On My Machine** — a command-line tool that creates Python and
JavaScript projects from templates, configures existing ones, and keeps the
small things around them under control: your PATH, the Windows context menu,
and the runtimes your work depends on.

## 🚀 Quick start

Install the tool, then create a project that is ready to run — virtual
environment, dependencies and git included.

```bash
uv tool install womm-cli
womm create official/python ./hello-womm --setup
```

[Get started](get-started.md) walks through it step by step, including what to
do when `womm` is not found after the install.

## 📚 Documentation

| Section                                  | What you will find                                             |
| :--------------------------------------- | :------------------------------------------------------------- |
| [Get started](get-started.md)            | Install WOMM and create your first project                     |
| [Guides](tasks/index.md)                 | One page per task: create, configure, templates, PATH, Windows |
| [Concepts](concepts/template-catalog.md) | The template catalog, the dependency strata, your WOMM data    |
| [Reference](reference/commands.md)       | Every command and option, file locations and variables         |
| [Troubleshooting](troubleshooting.md)    | Symptoms, causes and fixes                                     |
| [FAQ](faq.md)                            | Short answers to recurring questions                           |
| [Release notes](release-notes.md)        | What changed for you in each version                           |
| [Changelog](changelog.md)                | The full technical history, generated from the commits         |

## 📋 Requirements

- Windows, macOS or Linux. The context menu commands and `womm system
  refresh-env` are Windows-only.
- Python 3.13 or later. `uv tool install` provisions it for you if you do not
  have it.

## ⚖️ License

WOMM is released under the
[MIT License](https://github.com/neuraaak/WOMM/blob/main/LICENSE).
