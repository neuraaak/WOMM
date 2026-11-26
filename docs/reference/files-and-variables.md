# Files and variables

## Data directory

| Path                        | Content                                                                    | Created                  |
| :-------------------------- | :------------------------------------------------------------------------- | :----------------------- |
| `~/.womm/`                  | Everything WOMM keeps for you                                              | On first use             |
| `~/.womm/logs/`             | Log files of past runs                                                     | On first use             |
| `~/.womm/templates/`        | Catalog of your registered templates                                       | On first registration    |
| `~/.womm/backups/path/`     | PATH snapshots, named `.path_<YYYYMMDD_HHMMSS>.json`                       | Before every PATH change |
| `~/.womm/backups/registry/` | Context menu snapshots, named `context_menu_backup_<YYYYMMDD_HHMMSS>.json` | On backup                |
| `~/.womm/update-check.json` | Latest release seen on PyPI and when it was checked                        | On first update check    |

On Windows, `~` is `C:\Users\<you>`.

WOMM never writes code into this directory. Explicit setup and tooling-update
commands can write into a project after creation.

## Project update files

| Path                         | Content                                                      |
| :--------------------------- | :----------------------------------------------------------- |
| `.womm-template.json`        | Original generation provenance; preserved by updates         |
| `.womm-update.json`          | Successful tooling updates, versions and migrations          |
| `.womm-backups/update/<id>/` | Previous files and a manifest naming files originally absent |
| `.womm-update.lock`          | Exclusive apply lock; removed when the update finishes       |

Ignore `.womm-backups/` and `.womm-update.lock` in Git. Backups are local to
the project and can contain local configuration. A preview creates none of
these files. See [Update tooling](../tasks/configure-an-existing-project.md#update-an-official-projects-tooling)
for migration boundaries and recovery after a failed installation.

## Environment variables

| Variable               | Effect                                                        | Default   |
| :--------------------- | :------------------------------------------------------------ | :-------- |
| `WOMM_HOME`            | Absolute path used as the data directory instead of `~/.womm` | `~/.womm` |
| `WOMM_NO_UPDATE_CHECK` | Any non-empty value turns off the new-release notice          | Unset     |

## New-release notice

When a newer WOMM is published on PyPI, a command run in a terminal ends with a
yellow line on stderr naming the new version and the command that upgrades your
installation, such as `uv tool upgrade womm-cli`. Run alone, `womm` shows the
same check under its welcome panel, and says so when WOMM is up to date. WOMM
never upgrades itself.

PyPI is asked at most once a day; the answer is kept in
`~/.womm/update-check.json`. Without a network the check gives up after one
second and is not retried before the next day. It never runs when the output is
not a terminal, when the `CI` variable is set, or when `WOMM_NO_UPDATE_CHECK`
is set.

## Settings file

There is none. WOMM has no persistent configuration: every behaviour is decided
by the command and its options.

## Installed files

Installed with `uv tool install womm-cli`, the program lives in uv's tool
directory and the `womm` command is a shim in `~/.local/bin`. Neither is meant
to be edited; `uv tool upgrade womm-cli` replaces them.
