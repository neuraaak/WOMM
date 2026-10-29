# 🛠️ Works On My Machine (WOMM)

> ## ⚠️ This package has been renamed
>
> **`works-on-my-machine` is no longer maintained under this name on PyPI.**
> Development continues as **[`womm-cli`](https://pypi.org/project/womm-cli/)** —
> same tool, same `womm` command, same repository.
>
> ```bash
> pip uninstall works-on-my-machine
> pip install womm-cli
> ```
>
> `3.2.4` is the final release published under this name. The repository has
> moved to **[github.com/neuraaak/WOMM](https://github.com/neuraaak/WOMM)** and
> the documentation to **[neuraaak.github.io/WOMM](https://neuraaak.github.io/WOMM/)**.
>
> ### 🚫 Do not install `3.2.4`
>
> This release exists **only to carry this notice**. On PyPI it jumps straight
> from `2.6.8` to `3.2.4`: every version in between was developed but never
> published, and this build has never been validated through the PyPI install
> path. Treat it as a tombstone, not as working software — assume it may be
> broken or incomplete, and install
> **[`womm-cli`](https://pypi.org/project/womm-cli/)** instead.
>
> The name change is purely administrative: the PyPI name `womm` was already
> taken by an unrelated project, so `womm-cli` was chosen instead.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg?style=for-the-badge)](https://github.com/neuraaak/WOMM)
[![Version](https://img.shields.io/badge/Version-3.2.4-lightgrey.svg?style=for-the-badge)](https://github.com/neuraaak/WOMM)
[![PyPI](https://img.shields.io/badge/PyPI-works--on--my--machine-green.svg?style=for-the-badge&logo=pypi)](https://pypi.org/project/works-on-my-machine/)
[![Docs](https://img.shields.io/badge/Docs-Online-blue.svg?style=for-the-badge&logo=readthedocs)](https://neuraaak.github.io/WOMM/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Deprecated-red.svg?style=for-the-badge)](https://github.com/neuraaak/WOMM)
[![Tests](https://img.shields.io/badge/Tests-TODO-orange.svg?style=for-the-badge)](https://github.com/neuraaak/WOMM)

<!-- [![Coverage](https://img.shields.io/badge/Coverage-29%25-yellow.svg?style=for-the-badge)](https://github.com/neuraaak/WOMM) -->

![WOMM Logo](docs/assets/logo-min.png)

> **Universal development environment manager for Python and JavaScript**  
> 🚀 **One command to rule them all** - Automatic setup, cross-platform configuration, professional tooling

---

## 🎯 What is WOMM?

**Works On My Machine** is a comprehensive development environment manager that eliminates the "it works on my machine" problem. It provides a unified CLI tool that automatically sets up professional development environments for Python and JavaScript projects.

### ✨ **Key Features**

- 🚀 **One-Command Setup** - Complete project initialization with professional tooling
- 🔧 **Cross-Platform** - Works seamlessly on Windows, macOS, and Linux
- 🎯 **Smart Detection** - Automatically detects project types and applies appropriate configurations
- 📦 **Template System** - Create reusable project templates from existing projects
- 🛠️ **Professional Tooling** - Pre-configured with industry-standard tools (Black, ESLint, Prettier, etc.)
- 🔄 **Interactive Mode** - Guided setup with beautiful CLI interfaces
- 📚 **Comprehensive Documentation** - Complete guides for every feature

---

## 🚀 Quick Start

### **Installation**

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

### **Create Your First Project**

```bash
# Create a Python project with full tooling
womm new python my-awesome-app

# Create a JavaScript/React project
womm new javascript my-react-app --type react

# Let WOMM detect and setup automatically (interactive mode)
womm new --interactive
```

### **Setup Existing Projects**

```bash
# Setup Python project with professional tooling
womm setup python

# Setup JavaScript project with ESLint, Prettier, etc.
womm setup javascript

# Auto-detect and setup
womm setup detect
```

---

## 🎯 Available Commands

### **🆕 Project Creation**

```bash
womm new python <name>     # Create Python project with virtual env, Black, pytest
womm new javascript <name> # Create JavaScript project with ESLint, Prettier
womm new javascript <name> --type react # Create React project
womm new javascript <name> --type vue # Create Vue project
womm new --interactive    # Interactive project creation with auto-detection
```

### **⚙️ Project Setup**

```bash
womm setup python          # Setup Python project (dependencies, tools, config)
womm setup javascript      # Setup JavaScript project (npm, ESLint, etc.)
womm setup --interactive   # Interactive setup with auto-detection
```

### **🔍 Code Quality**

```bash
womm lint python           # Lint Python code (Black, isort, flake8)
womm lint javascript       # Lint JavaScript code (ESLint, Prettier)
womm lint all              # Lint all supported code in project
womm spell check           # Check spelling in project files
```

### **📦 Template Management**

```bash
womm template create       # Create template from current project
womm template list         # List available templates
womm template info <name>  # Show template details
womm template delete <name> # Delete template
```

### **🔧 System Management**

```bash
womm system detect         # Detect system information and tools
womm system install <tools> # Install prerequisites (python, node, git)
```

### **🖱️ Windows Integration**

```bash
womm context register      # Register WOMM in Windows context menu
womm context unregister    # Remove from context menu
womm context list          # List registered entries
```

---

## 🏗️ What WOMM Sets Up

### **🐍 Python Projects**

- ✅ **Virtual Environment** with `venv`
- ✅ **Code Formatting** with Black and isort
- ✅ **Linting** with flake8 and ruff
- ✅ **Testing** with pytest and coverage
- ✅ **Pre-commit Hooks** for quality assurance
- ✅ **VSCode Configuration** for consistent development
- ✅ **pyproject.toml** with modern Python packaging
- ✅ **Development Scripts** for common tasks

### **🟨 JavaScript Projects**

- ✅ **Package Management** with npm/yarn
- ✅ **Code Formatting** with Prettier
- ✅ **Linting** with ESLint
- ✅ **Testing** with Jest
- ✅ **Git Hooks** with Husky
- ✅ **VSCode Configuration** for JavaScript development
- ✅ **TypeScript Support** (optional)
- ✅ **Modern ES6+ Configuration**

### **🔧 Professional Tooling**

- ✅ **Cross-Platform Compatibility**
- ✅ **Consistent Code Style** across team
- ✅ **Automated Quality Checks**
- ✅ **Integrated Development Environment**
- ✅ **Best Practices** out of the box

---

## 📚 Documentation

### **📖 [Complete Documentation](docs/index.md)**

- **📋 [CLI Overview](docs/cli/index.md)** - All available commands and options
- **🔧 [Commands Reference](docs/cli/commands.md)** - Common commands quick reference
- **🆕 [Project Creation](docs/cli/NEW.md)** - Create Python, JavaScript, React, and Vue projects
- **⚙️ [Project Setup](docs/cli/setup.md)** - Configure existing projects with professional tooling
- **🔍 [Linting](docs/cli/lint.md)** - Code quality and linting tools
- **📝 [Spell Check](docs/cli/spell.md)** - Spell checking and dictionaries
- **📦 [Templates](docs/cli/templates.md)** - Template management system
- **🛠️ [System Tools](docs/cli/system.md)** - System detection and management
- **🖱️ [Context Menu](docs/cli/context.md)** - Windows context menu integration

### **🔌 [API Reference](docs/api/index.md)**

- **🏗️ [Architecture](docs/api/architecture.md)** - Dependency management architecture
- **⚡ [CLI Architecture](docs/api/cli-architecture.md)** - Unified CLI design
- **📦 [Templates API](docs/api/templates.md)** - Template system reference
- **⚠️ [Exceptions](docs/api/exceptions.md)** - Error handling architecture
- **📊 [Logging](docs/api/logging.md)** - Normalized logging patterns

---

## 🎯 Use Cases

### **👨‍💻 Individual Developers**

- **Quick Project Setup** - Start coding in minutes, not hours
- **Consistent Environments** - Same setup across all your machines
- **Professional Standards** - Industry-standard tooling without the hassle

### **👥 Development Teams**

- **Standardized Workflows** - Everyone uses the same tools and configurations
- **Onboarding** - New team members can start contributing immediately
- **Quality Assurance** - Automated code quality checks for all projects

### **🏢 Organizations**

- **Template Library** - Create and share project templates across teams
- **Best Practices** - Enforce coding standards and development workflows
- **Cross-Platform** - Works consistently across Windows, macOS, and Linux

---

## 🛠️ Technical Architecture

### **Core Components**

- **CLI Interface** - Modern Click-based command-line interface
- **Project Managers** - Language-specific project creation and setup
- **Template System** - Dynamic template generation and management
- **System Detection** - Automatic detection of tools and environments
- **UI Components** - Rich terminal interfaces with progress tracking

### **Supported Platforms**

- **Windows** - Full support with batch scripts and PowerShell
- **macOS** - Native Unix-like environment support
- **Linux** - Complete compatibility with various distributions

### **Language Support**

- **Python** - 3.8+ with modern tooling ecosystem
- **JavaScript** - Node.js with modern development tools
- **Extensible** - Framework for adding more languages

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### **Development Setup**

```bash
# Clone and setup development environment
git clone https://github.com/neuraaak/WOMM.git
cd works-on-my-machine

# Install in development mode
pip install -e .

# Run tests
pytest

# Run linting
womm lint python
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Click** - For the excellent CLI framework
- **Rich** - For beautiful terminal interfaces
- **InquirerPy** - For interactive command-line prompts
- **Black, ESLint, Prettier** - For code quality tools
- **The Python and JavaScript communities** - For amazing development tools

---

_"It works on my machine, and now it will work on yours too!"_ 🚀
