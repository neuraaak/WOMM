# Use the Windows context menu

Add your own entries to the Windows right-click menu, list what is registered,
and restore a previous state from a backup.

!!! warning "Windows only"

    `womm context` reads and writes the Windows registry. On macOS and Linux the
    command group exists but has nothing to act on.

## 🔧 Prerequisites

- WOMM installed on Windows — see [Get started](../get-started.md).
- The script or executable you want to launch from the menu.

## 📝 Steps

### Register the usual WOMM entries

```bash
womm context quick-setup
```

### Register your own entry

```bash
womm context register --target "C:\tools\build.ps1" --label "Build project" --background
```

Choose where the entry appears with the scope options:

| Option         | Where the entry appears                             |
| :------------- | :-------------------------------------------------- |
| `--background` | Right-click on the empty space inside a folder      |
| `--root`       | Right-click on a drive                              |
| `--file`       | Right-click on a single selected file               |
| `-F, --files`  | Right-click on a multiple file selection            |
| `--file-types` | Only for a family of types, such as `image`, `text` |
| `--extension`  | Only for given extensions, such as `.py`, `.js`     |

`--icon` takes a path or `auto` (the default) to pick the icon from the target.
`-I, --interactive` walks you through the same choices.

### See what is registered

```bash
womm context list
```

### Remove an entry

```bash
womm context unregister --remove "Build project"
```

`--remove` is required and takes the key name as stored in the registry, which
`womm context list` prints.

### Back up and restore

```bash
womm context backup create
womm context backup list
womm context backup show context_menu_backup_20261029_120000.json
womm context backup restore context_menu_backup_20261029_120000.json
```

To bring back only part of a backup, pick the entries you want:

```bash
womm context backup cherry-pick
```

## ✅ Result

The entry appears in the right-click menu for the scope you chose, and
`womm context list` counts it. A backup taken before a change can restore the
previous state, in full or entry by entry.

If the entry does not show up, see
[Troubleshooting](../troubleshooting.md#a-context-menu-entry-does-not-appear).

## ➡️ Next steps

- [Your WOMM data](../concepts/your-womm-data.md) — where registry backups are
  kept.
