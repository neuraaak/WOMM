# Dependencies

WOMM needs external programs to do its work, and it sorts them into two strata.

**Runtimes** come first: Python 3.13 or later, Node.js 18 or later, and git
2.30 or later. They are the programs a project is built on.

**Runtime package managers** come second: pip and uv for Python, npm and yarn
for Node.js. Each one depends on its runtime — uv is only useful once Python is
there.

The two strata are hierarchical, which is why `womm deps check` succeeds only
when every runtime is installed **and** at least one package manager is
available: a runtime without a package manager cannot install anything.

## WOMM never installs them

`womm deps` reports, it does not install. Installing a runtime touches your
whole machine, often needs administrator rights, and every operating system does
it differently — so that decision stays yours. Use your own package manager
(winget, Homebrew, apt, or the installer from the vendor).

What WOMM does install is inside a project: a virtual environment and the
project's own dependencies, when you ask for them with `--setup` or
`womm setup`.

## ➡️ Next steps

- [Check what WOMM needs](../tasks/check-dependencies.md) — run the report.
- [Configure an existing project](../tasks/configure-an-existing-project.md) —
  what WOMM does install, and where.
