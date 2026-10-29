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
   tests, CI and shared editor settings.

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

!!! warning "`--force` merges, it does not overwrite everything"

    `--force` allows rendering into a non-empty directory. Files the template
    produces replace their counterparts; everything else is left in place. Run
    the same command with `--pretend` first if you are unsure what it touches.

## ✅ Result

The destination holds the rendered project. With `--setup`, the environment is
ready and git is initialized.

The official templates do not keep an answers file in the project, so a
creation is not replayable: to change an answer, create again into another
destination.

If the command stops on a non-empty destination or on a missing runtime, see
[Troubleshooting](../troubleshooting.md#the-destination-is-not-empty).

## ➡️ Next steps

- [Manage templates](manage-templates.md) — register your own template.
- [The template catalog](../concepts/template-catalog.md) — official and user
  templates, and where the catalog lives.
