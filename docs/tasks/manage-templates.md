# Manage templates

Inspect the template catalog, register a template of your own, or scaffold a new
one from scratch.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).
- To register a template: a local directory holding a `copier.yml` (or
  `copier.yaml`) file. Remote sources (a git URL) are not supported yet.
- To scaffold one: nothing more. `womm template init` writes the skeleton.
- To build one from a project: the project must be the root of a git
  repository. Only its tracked files are read.

## 📝 Steps

### List and inspect

```bash
womm template list
womm template show official/python
```

`list` shows every entry with its version and description, official ones first.
`show` prints one entry in detail. A short name works when it is unambiguous:
`womm template show python`.

### Register your own

```bash
womm template add mytpl ./templates/my-template
```

WOMM copies the directory into `~/.womm/templates/copies/` and renders from that
copy, so moving, renaming or archiving the original breaks nothing. Everything
is copied except `.git`: register a clean template directory, not one holding a
`.venv` or `node_modules`.

The identifier is a name, optionally prefixed by one namespace of your own:
`mytpl` or `neuraaak/mytpl`. WOMM files it under the `user/` origin, so these
are listed as `user/mytpl` and `user/neuraaak/mytpl`. `official` and `user` are
reserved and cannot be used as a namespace. Each part names a directory of the
copy: letters, digits, `.`, `_` and `-`, starting and ending with a letter or
digit.

Prefer to be guided? `womm template add -I` asks for the identifier and the
directory, shows the entry it read from `copier.yml`, and registers it only
once you confirm. `update -I` and `remove -I` let you pick the entry from a
list.

Edited your template since? `womm template update mytpl` copies it again from
the directory it was registered from; `show -v` names that directory.

To let `womm create --setup` prepare projects made from your template, declare
their language in `copier.yml`:

```yaml
_womm:
  setup:
    language: python  # or javascript
```

### Scaffold a new template

```bash
womm template init ./templates/my-template
```

WOMM renders a Copier template skeleton: a `copier.yml`, a `template/` directory
and the metadata the catalog needs. `--data KEY=VALUE`, `--defaults` and
`--force` behave as in [Create a project](create-a-project.md). With `-I`, WOMM
asks for the destination if you leave it out, then offers to register the
skeleton in the catalog.

### Build a template from an existing project

```bash
womm template init ./templates/webview --from ../flash-excel --exclude docs/
```

The template holds a copy of every file git tracks in the project, so its
configuration, CI and scripts come along. WOMM reads the project's name in
`pyproject.toml` (or `package.json`) and replaces it with questions:

| In the project | In the template | Asked                                 |
| :------------- | :-------------- | :------------------------------------ |
| `Flash-Excel`  | `project_name`  | Yes                                   |
| `flash-excel`  | `project_slug`  | No, derived from `project_name`       |
| `flash_excel`  | `package_name`  | Yes, defaults to the derived name     |

What to expect:

- A name is replaced only where it stands alone: `flash-excel-ui` or
  `FlashExcelAPI` stay as they are. The same rule applies to file names, so
  `flash-excel.spec` is renamed. The report counts the lines that still
  mention the name; review them with `-v`.
- When two forms are the same text, as for a project named `foo`, the
  strictest variable available wins: `package_name` drives all of them, or
  `project_slug` when no Python package was found.
- Version, dependencies, authors, URLs, license and publishing settings stay
  as in the project, except where the name appears. Lockfiles are kept too:
  regenerate them before any `--frozen` install.
- Files where a name was replaced are rendered with LF line endings. The other
  files are copied byte for byte.
- `--exclude` takes a pattern on the path relative to the project; end it with
  `/` to leave out a whole folder. WOMM warns about a pattern that matched
  nothing.
- `.env` files (except `.env.example`), keys, certificates, credentials and
  `.tufup` files are always left out, even when tracked. This does not prove
  that no secret remains: read the template before sharing it.
- Symbolic links and git submodules are left out. WOMM refuses the extraction
  when the project has unmerged files, or when two paths differ only by the
  project's name and could render to the same file. Other clashes remain
  possible: a file named `new-app.txt` and a renamed `flash-excel.txt` collide
  if you answer `new-app`.

### Refresh an entry, move it, or drop it

```bash
womm template update mytpl                          # copy again from its origin
womm template update mytpl ./templates/my-template-v2  # copy from a new origin
womm template remove mytpl
```

If the origin has moved, `update` without a directory says so: pass the new
location. `remove` unregisters the entry and deletes WOMM's copy; your template
directory stays on disk. Only user entries can be updated or removed — the
official ones ship inside WOMM.

An entry registered before WOMM 5.5.0 still points at your directory and is
rendered from it directly: if it is a git repository, from its current commit
plus uncommitted changes. `womm template update` turns it into a copy.

## ✅ Result

`womm template list` reflects the change, and
`womm create user/mytpl ./my-app` renders your template like any official one.

If `add` refuses the source, it is missing a `copier.yml` — see
[Troubleshooting](../troubleshooting.md#womm-template-add-says-not-a-copier-template).

## ➡️ Next steps

- [Create a project](create-a-project.md) — render any catalog entry.
- [The template catalog](../concepts/template-catalog.md) — where the catalog
  lives and what official means.
