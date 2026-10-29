# The template catalog

The catalog is the list of templates WOMM can render. It has two origins, and
both appear in `womm template list`.

**Official templates** ship inside WOMM itself. There are two —
`official/python` and `official/javascript` — and they are read-only: they are
updated when you upgrade WOMM, never by you.

**User templates** are directories on your machine that you register under the
`user/` namespace. WOMM stores the registration, not the template: the entry
points at your directory, and your files stay where they are.

Every template is a [Copier](https://copier.readthedocs.io/) template: a
`copier.yml` declaring the questions, and a `template/` directory whose files
are rendered with your answers. `womm create` asks those questions and writes
the result; it adds the catalog and the environment setup around Copier, nothing
more.

A template source must be a local directory. A git URL is not supported yet.

## ➡️ Next steps

- [Manage templates](../tasks/manage-templates.md) — register, scaffold, update
  or drop an entry.
- [Create a project](../tasks/create-a-project.md) — render an entry.
