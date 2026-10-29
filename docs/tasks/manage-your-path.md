# Manage your PATH

Add or remove a directory from your user PATH, and undo the change from a
backup.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).
- For `add`: a directory that exists and holds at least one executable.

!!! warning "Your PATH is backed up before every change"

    `womm path add` and `womm path remove` back up the current PATH before
    touching it, so `womm path backup restore` always has a way back.

## 📝 Steps

### See what is on your PATH

```bash
womm path list
```

### Add a directory

```bash
womm path add "C:\tools\bin"
```

The directory must exist and contain an executable, otherwise WOMM refuses the
change. Open a new terminal to pick up the new PATH — on Windows,
`womm system refresh-env` refreshes it without reopening.

### Remove a directory

```bash
womm path remove "C:\tools\bin"
```

The directory does not have to exist: dropping the leftover entry of a tool you
uninstalled is the usual reason to run this.

### Undo from a backup

```bash
womm path backup list
womm path backup show .path_20261029_120000.json
womm path backup restore .path_20261029_120000.json
```

`restore` without a name lets you pick one from the list. `show` and `restore`
take a bare backup file name, as printed by `backup list` — not a path.

To take a snapshot before doing something risky by hand:

```bash
womm path backup create
```

## ✅ Result

`womm path list` shows the entry added or gone, and `womm path backup list`
shows the backup that was taken just before the change.

If the new entry is not visible to your other programs, see
[Troubleshooting](../troubleshooting.md#a-new-path-entry-is-not-visible).

## ➡️ Next steps

- [Your WOMM data](../concepts/your-womm-data.md) — where the backups are kept.
