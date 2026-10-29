# FAQ

## Why is the package called `womm-cli` and the command `womm`?

The name `womm` was already taken on PyPI by an unrelated project, so the
package is published as `womm-cli`. You only ever type that name when you
install or upgrade. Everything else — the command, the repository, the data
directory — is `womm`.

## Do I need Python installed?

No. `uv tool install womm-cli` downloads the Python version WOMM needs and keeps
it in its own isolated environment. Your system Python, if you have one, is left
alone.

## Does WOMM install Python, Node.js or git for me?

No. It reports what is available with `womm deps check` and leaves the
installing to you — see [Dependencies](concepts/dependencies.md). Inside a
project it does install, when you ask: virtual environment and dependencies.

## Does WOMM change my PATH on its own?

No. Your PATH changes only when you run `womm path add` or `womm path remove`,
and each of those takes a backup first. The installer does not touch it either:
`uv tool update-shell` is a command you choose to run.

## Is WOMM Windows-only?

No. `womm context` and `womm system refresh-env` are Windows-only because they
act on the registry and the Windows environment. Everything else works on
Windows, macOS and Linux.

## Where does WOMM keep my data, and does an upgrade erase it?

In `~/.womm`, and no. Upgrading or uninstalling the program leaves your
templates, backups and logs untouched — see
[Your WOMM data](concepts/your-womm-data.md).

## Can I use a template hosted on a git repository?

Not yet. `womm template add` takes a local directory. Clone the template first,
then register the clone.

## How do I upgrade or remove WOMM?

```bash
uv tool upgrade womm-cli
uv tool uninstall womm-cli
```

Neither touches `~/.womm`.
