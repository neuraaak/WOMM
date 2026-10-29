# Your WOMM data

Everything WOMM keeps for you lives in one directory: `~/.womm` — that is
`C:\Users\<you>\.womm` on Windows. It holds data only, never code.

| Inside `~/.womm`    | What it holds                                  |
| :------------------ | :--------------------------------------------- |
| `logs/`             | The log files of past runs                     |
| `templates/`        | The catalog of the templates you registered    |
| `backups/path/`     | PATH snapshots, taken before every PATH change |
| `backups/registry/` | Windows context menu snapshots                 |

Three consequences worth knowing:

- **Upgrading or removing WOMM does not touch it.** `uv tool upgrade womm-cli`
  and `uv tool uninstall womm-cli` replace or remove the program; your
  templates, backups and logs stay.
- **It is yours to inspect.** The backups are plain JSON files, so you can read
  one without WOMM if you ever need to.
- **You can move it.** Set the `WOMM_HOME` environment variable to another
  absolute path and WOMM uses that directory instead — useful to keep a project
  machine isolated, or to test without touching your real data.

There is no settings file: WOMM has no persistent configuration of its own.
Behaviour is decided by the command and its options, every time.

## ➡️ Next steps

- [Files and variables](../reference/files-and-variables.md) — the exact paths
  and the variable.
- [Diagnose your installation](../tasks/diagnose-your-installation.md) — check
  the directory WOMM resolves and whether it is writable.
