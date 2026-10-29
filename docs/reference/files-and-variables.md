# Files and variables

## Data directory

| Path                        | Content                                                                    | Created                  |
| :-------------------------- | :------------------------------------------------------------------------- | :----------------------- |
| `~/.womm/`                  | Everything WOMM keeps for you                                              | On first use             |
| `~/.womm/logs/`             | Log files of past runs                                                     | On first use             |
| `~/.womm/templates/`        | Catalog of your registered templates                                       | On first registration    |
| `~/.womm/backups/path/`     | PATH snapshots, named `.path_<YYYYMMDD_HHMMSS>.json`                       | Before every PATH change |
| `~/.womm/backups/registry/` | Context menu snapshots, named `context_menu_backup_<YYYYMMDD_HHMMSS>.json` | On backup                |

On Windows, `~` is `C:\Users\<you>`.

WOMM never writes code into this directory, and never writes into a project
after it has been created.

## Environment variables

| Variable    | Effect                                                        | Default   |
| :---------- | :------------------------------------------------------------ | :-------- |
| `WOMM_HOME` | Absolute path used as the data directory instead of `~/.womm` | `~/.womm` |

## Settings file

There is none. WOMM has no persistent configuration: every behaviour is decided
by the command and its options.

## Installed files

Installed with `uv tool install womm-cli`, the program lives in uv's tool
directory and the `womm` command is a shim in `~/.local/bin`. Neither is meant
to be edited; `uv tool upgrade womm-cli` replaces them.
