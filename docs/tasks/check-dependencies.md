# Check what WOMM needs

Find out which runtimes and package managers are available on your machine
before WOMM uses them.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).

!!! note "WOMM installs nothing"

    These commands only report. Installing a missing runtime is up to you and
    your operating system's package manager — see
    [Dependencies](../concepts/dependencies.md).

## 📝 Steps

1. Check availability:

    ```bash
    womm deps check
    ```

    The exit status is `0` when every runtime is installed and at least one
    runtime package manager is available. Add `-v` to see the version of each
    component.

2. See the full picture in one table:

    ```bash
    womm deps status
    ```

3. See what WOMM knows about, independently of your machine:

    ```bash
    womm deps list
    ```

## ✅ Result

You know which of the runtimes (Python, Node.js, git) and which runtime package
managers (pip, uv, npm, yarn) WOMM can rely on, and which ones you need to
install yourself.

A command that fails on a missing runtime is covered in
[Troubleshooting](../troubleshooting.md#a-command-fails-on-a-missing-runtime).

## ➡️ Next steps

- [Dependencies](../concepts/dependencies.md) — why there are two strata and why
  WOMM never installs.
- [Diagnose your installation](diagnose-your-installation.md) — what WOMM itself
  resolves.
