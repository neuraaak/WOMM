# Commands

Every command, as `womm --help` reports it. `-h, --help` works on each one, and
`-v, --verbose` on most.

## Projects

| Command                     | What it does                               |
| :-------------------------- | :----------------------------------------- |
| `womm create TEMPLATE DEST` | Render a catalog template into `DEST`      |
| `womm setup detect`         | Detect the project type, then configure it |
| `womm setup python`         | Configure an existing Python project       |
| `womm setup javascript`     | Configure an existing JavaScript project   |

### `womm create` options

| Option             | Effect                                          |
| :----------------- | :---------------------------------------------- |
| `--data KEY=VALUE` | Pre-fill one template answer. Repeatable.       |
| `--defaults`       | Use the template defaults instead of prompting. |
| `--force`          | Render into a destination that is not empty.    |
| `--pretend`        | Simulate the rendering, write nothing.          |
| `--setup`          | Prepare the environment after rendering.        |
| `-v, --verbose`    | Show the detailed output.                       |

### `womm setup` options

| Option                 | `detect` | `python` | `javascript` |     |     |
| :--------------------- | :------- | :------- | :----------- | --- | --- |
| `-p, --path DIRECTORY` | yes      | yes      | yes          |     |     |
| `-I, --interactive`    | yes      | yes      | yes          |     |     |
| `-v, --verbose`        | yes      | yes      | yes          |     |     |
| `--install-deps`       | no       | yes      | yes          |     |     |
| `--setup-dev-tools`    | no       | yes      | no           |     |     |
| `--setup-git-hooks`    | no       | yes      | yes          |     |     |
| `--virtual-env`        | no       | yes      | no           |     |     |
| `-t, --type TYPE`      | no       | no       | yes          |     |     |

## Templates

| Command                            | What it does                             |
| :--------------------------------- | :--------------------------------------- |
| `womm template list`               | List every catalog entry, official first |
| `womm template show IDENTIFIER`    | Show one entry in detail                 |
| `womm template add NAME SOURCE`    | Register a local template under `user/`  |
| `womm template init DESTINATION`   | Scaffold a new Copier template skeleton  |
| `womm template update NAME SOURCE` | Point a user entry at another source     |
| `womm template remove NAME`        | Unregister a user entry                  |

`womm template init` also takes `--data KEY=VALUE`, `--defaults` and `--force`.

## Dependencies

| Command            | What it does                                              |
| :----------------- | :-------------------------------------------------------- |
| `womm deps check`  | Probe both strata; exit `0` when the requirements are met |
| `womm deps status` | Full status table, with versions                          |
| `womm deps list`   | Static inventory of what WOMM knows about                 |

## PATH

| Command                           | What it does                                        |
| :-------------------------------- | :-------------------------------------------------- |
| `womm path list`                  | List the entries of your current PATH               |
| `womm path add DIRECTORY`         | Add a directory that exists and holds an executable |
| `womm path remove DIRECTORY`      | Remove an entry, existing or not                    |
| `womm path backup create`         | Snapshot the current PATH                           |
| `womm path backup list`           | List the snapshots                                  |
| `womm path backup show NAME`      | Print the content of one snapshot                   |
| `womm path backup restore [NAME]` | Restore a snapshot; interactive without `NAME`      |

## Windows context menu

| Command                                | What it does                                |
| :------------------------------------- | :------------------------------------------ |
| `womm context quick-setup`             | Register the usual WOMM entries             |
| `womm context register`                | Register your own entry (see options below) |
| `womm context list`                    | List the registered entries                 |
| `womm context unregister --remove KEY` | Remove one entry by its registry key name   |
| `womm context backup create`           | Snapshot the current entries                |
| `womm context backup list`             | List the snapshots                          |
| `womm context backup show NAME`        | Print the content of one snapshot           |
| `womm context backup restore NAME`     | Restore a snapshot                          |
| `womm context backup cherry-pick`      | Restore only the entries you select         |

### `womm context register` options

| Option              | Effect                                                    |
| :------------------ | :-------------------------------------------------------- |
| `--target PATH`     | Script or executable the entry launches                   |
| `-l, --label TEXT`  | Label shown in the menu                                   |
| `--icon TEXT`       | Icon path, or `auto` to take it from the target (default) |
| `--background`      | Register for the background of a folder                   |
| `--root`            | Register for drives                                       |
| `--file`            | Register for a single selected file                       |
| `-F, --files`       | Register for a multiple file selection                    |
| `--file-types TEXT` | Register for a family of types, such as `image` or `text` |
| `--extension TEXT`  | Register for given extensions, such as `.py` or `.js`     |
| `-I, --interactive` | Guided setup                                              |

## System and diagnostic

| Command                   | What it does                                     |
| :------------------------ | :----------------------------------------------- |
| `womm doctor`             | Report the installed runtime; changes nothing    |
| `womm system detect`      | Detect system information and available tools    |
| `womm system refresh-env` | Refresh the environment variables (Windows only) |
| `womm --version`          | Print the version                                |
