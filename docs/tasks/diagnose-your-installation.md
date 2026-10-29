# Diagnose your installation

Check what WOMM resolves on your machine — version, executable, data directory —
and refresh your environment after a change.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).

## 📝 Steps

1. Ask WOMM about itself:

    ```bash
    womm doctor
    ```

    The report lists the version, the `womm` command your shell resolves, the
    data directory and whether it is writable, and the number of registered
    context menu entries. Add `-v` to also see the resolved executable path.
    The command changes nothing.

2. Ask WOMM about your machine:

    ```bash
    womm system detect
    ```

3. On Windows, after installing a tool or changing your PATH, refresh the
   environment without opening a new terminal:

    ```bash
    womm system refresh-env
    ```

## ✅ Result

You know which installation of WOMM is answering, where its data lives, and
which tools it can see. Nothing on your machine was modified.

If `womm doctor` reports a data directory that is not writable, or no `womm` on
your PATH, see [Troubleshooting](../troubleshooting.md).

## ➡️ Next steps

- [Check what WOMM needs](check-dependencies.md) — the runtimes behind the
  commands.
- [Your WOMM data](../concepts/your-womm-data.md) — what lives in the data
  directory.
