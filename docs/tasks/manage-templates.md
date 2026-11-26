# Manage templates

Inspect the template catalog, register a template of your own, or scaffold a new
one from scratch.

## 🔧 Prerequisites

- WOMM installed — see [Get started](../get-started.md).
- To register a template: a local directory holding a `copier.yml` (or
  `copier.yaml`) file. Remote sources (a git URL) are not supported yet.
- To scaffold one: nothing more. `womm template init` writes the skeleton.

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

The identifier is a plain name — no slash, no path. WOMM files it under the
`user/` namespace, so the entry above is listed as `user/mytpl`. The `official/`
namespace is reserved.

Prefer to be guided? `womm template add -I` asks for the identifier and the
directory, shows the entry it read from `copier.yml`, and registers it only
once you confirm. `update -I` and `remove -I` let you pick the entry from a
list.

`list` and `show` read the version and description from the template's
`copier.yml` each time, so editing them needs no re-registration.

If the directory is a git repository, WOMM renders what is in it now: the
current commit plus any uncommitted changes, never an older tag. When
uncommitted changes are included, `womm create` says so in a warning.

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

### Point an entry elsewhere, or drop it

```bash
womm template update mytpl ./templates/my-template-v2
womm template remove mytpl
```

`remove` unregisters the entry; your template directory stays on disk. Only
user entries can be updated or removed — the official ones ship inside WOMM.

## ✅ Result

`womm template list` reflects the change, and
`womm create user/mytpl ./my-app` renders your template like any official one.

If `add` refuses the source, it is missing a `copier.yml` — see
[Troubleshooting](../troubleshooting.md#womm-template-add-says-not-a-copier-template).

## ➡️ Next steps

- [Create a project](create-a-project.md) — render any catalog entry.
- [The template catalog](../concepts/template-catalog.md) — where the catalog
  lives and what official means.
