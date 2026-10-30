# GitHub Actions workflows

The workflows validate WOMM, publish new versions to PyPI, and maintain the
versioned documentation on GitHub Pages.

| Workflow              | Role                                                                          |
| --------------------- | ----------------------------------------------------------------------------- |
| `00-install-deps.yml` | Prime the uv dependency cache.                                                |
| `01-ci.yml`           | Run the quality and test gates.                                               |
| `02-tag-sync.yml`     | Check the version, create a new tag if needed, then call publishing and docs. |
| `03-publish.yml`      | Build the package and publish a new version to PyPI.                          |
| `04-docs.yml`         | Validate docs on pull requests; deploy versioned docs after publishing.       |

## Documentation deployment

`04-docs.yml` builds the site with MkDocs and uses Mike to store published
versions on `gh-pages`:

| `tag_action` | Result                                                                    |
| ------------ | ------------------------------------------------------------------------- |
| `create`     | Deploy the package version, move `latest`, and point the site root to it. |
| `skip`       | Update `dev` from the current `main` branch.                              |
| `preview`    | Build a versioned preview without pushing.                                |

The release cascade in `02-tag-sync.yml` runs documentation **after** package
publishing. A pull request only builds the site and receives no write access.
Manual runs of `04-docs.yml` default to `preview`. Deploying `create` or `skip`
manually requires selecting `main` and the corresponding action.

The current `v4.0.0` tag predates Mike. After merging this workflow, run
`04 · Docs` manually on `main` with `tag_action=create` and `version=4.0.0` to
publish the first `latest` version. Later releases update it automatically.

GitHub Pages must use **Deploy from a branch**, with `gh-pages` as the branch
and `/ (root)` as the folder.

## Local checks

```bash
uv sync --group dev --group test --group docs
uv run --no-sync poe docs-build
```
