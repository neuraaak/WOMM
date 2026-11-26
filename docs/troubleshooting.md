# Troubleshooting

One entry per problem, named as you would describe it.

## `womm` is not found after the install

**Symptom** — `uv tool install womm-cli` succeeded, but your shell answers
`womm: command not found` or `'womm' is not recognized`.

**Cause** — uv installs the command as a shim in `~/.local/bin`, and that
directory is not on your PATH yet.

**Fix**

1. Let uv add it:

    ```bash
    uv tool update-shell
    ```

2. Open a new terminal. On Windows you can refresh the current one instead:

    ```bash
    womm system refresh-env
    ```

3. Still nothing? Call the shim directly to confirm the install itself is fine —
   `~/.local/bin/womm --version` — then check your shell profile for a line that
   resets `PATH`.

## The destination is not empty

**Symptom** — `womm create` stops with `Destination is not empty`, and lists
what it found.

**Cause** — WOMM refuses to render into a directory that already holds files,
so it cannot silently mix a template with your work.

**Fix**

1. Render into a fresh directory, or
2. Preview what a merge would write:

    ```bash
    womm create official/python ./my-app --pretend --force
    ```

3. If the result is what you want, run the same command without `--pretend`.
   Files produced by the template replace their counterparts; everything else is
   left alone.

## `womm setup detect` picks the wrong language

**Symptom** — the detection reports a project type you did not expect, or exits
with `No suitable project type detected`.

**Cause** — detection reads the markers in the directory (`pyproject.toml`,
`package.json`, and so on). A mixed or empty project leaves it undecided.

**Fix** — name the language yourself:

```bash
womm setup python
womm setup javascript --type react
```

## `womm template add` says "not a Copier template"

**Symptom** — registering a directory fails with `Not a Copier template`.

**Cause** — the source has no `copier.yml` or `copier.yaml` at its root, or it
is a remote URL, which is not supported yet.

**Fix**

1. Check that the directory holds a `copier.yml` or `copier.yaml`.
2. For a remote template, clone it first, then register the clone.
3. To start a template from scratch, let WOMM scaffold one:

    ```bash
    womm template init ./templates/my-template
    ```

## A command fails on a missing runtime

**Symptom** — a `--setup` or `womm setup` step fails, saying a runtime or
package manager is unavailable.

**Cause** — WOMM reports dependencies, it never installs them.

**Fix**

1. See what is missing:

    ```bash
    womm deps check -v
    ```

2. Install it with your own package manager (winget, Homebrew, apt, or the
   vendor installer).
3. On Windows, refresh the environment, then run the command again:

    ```bash
    womm system refresh-env
    ```

## A new PATH entry is not visible

**Symptom** — `womm path list` shows the directory, but your other programs
cannot find the executable.

**Cause** — a process reads the PATH when it starts. The terminal and the
programs already open still hold the old one.

**Fix**

1. On Windows, refresh the current terminal:

    ```bash
    womm system refresh-env
    ```

2. Otherwise, open a new terminal. Programs started before the change need to be
   restarted too.

## A context menu entry does not appear

**Symptom** — `womm context register` succeeded, but the entry is missing when
you right-click.

**Cause** — the entry was registered for another scope than the one you are
testing: the background of a folder, a drive, a single file and a multiple
selection are four different places.

**Fix**

1. Check what is registered, and for which scope:

    ```bash
    womm context list
    ```

2. Register the scope you actually use — for example the folder background:

    ```bash
    womm context register --target "C:\tools\build.ps1" --label "Build project" --background
    ```

3. If an entry has to go, remove it by its registry key name:

    ```bash
    womm context unregister --remove "Build project"
    ```

## `womm doctor` says the data directory is not writable

**Symptom** — the report shows `Data directory: … (not writable)`.

**Cause** — `~/.womm` (or the path in `WOMM_HOME`) belongs to another user, sits
on a read-only volume, or is blocked by a policy.

**Fix**

1. Check the owner and permissions of the directory the report prints.
2. Or point WOMM somewhere you own:

    ```bash
    setx WOMM_HOME "D:\womm-data"      # Windows, new terminals
    export WOMM_HOME="$HOME/womm-data" # macOS, Linux
    ```

3. Run `womm doctor` again to confirm.

## A `womm context` or `refresh-env` command does nothing

**Symptom** — on macOS or Linux, these commands have no effect.

**Cause** — both act on Windows mechanisms: the registry for the context menu,
and the Windows environment for `refresh-env`.

**Fix** — none needed: they are Windows-only by design. Every other command
works on all three platforms.
